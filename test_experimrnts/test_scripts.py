#!/usr/bin/env python3
"""
批量运行 floorplan 实验，记录指标并计算统计信息。
用法示例:
    python run_experiments.py --num-runs 100 --white-space-ratio 0.1
"""

import argparse
import subprocess
import sys
import random
import re
import csv
import os
import json
from pathlib import Path
from datetime import datetime
import statistics
from typing import Dict, List, Optional, Tuple

# yaml 为可选导入，未安装时在 run_tuning 中报友好提示
try:
    import yaml
except ImportError:
    yaml = None


# ---------- 参数解析 ----------
def parse_args():
    parser = argparse.ArgumentParser(description="批量运行 hw3_dbg 并收集结果")
    parser.add_argument("--executable", type=str, default="./bin/hw3_dbg",
                        help="可执行文件路径（相对于脚本位置）")
    parser.add_argument("--hardblocks", type=str, default="./testcase/n100.hardblocks",
                        help="hardblocks 文件路径")
    parser.add_argument("--nets", type=str, default="./testcase/n100.nets",
                        help="nets 文件路径")
    parser.add_argument("--terminals", type=str, default="./testcase/n100.pl",
                        help="terminals 文件路径")
    parser.add_argument("--white_space_ratio", type=float, default=0.1,
                        help="空白比例")
    parser.add_argument("--num_runs", type=int, default=20,
                        help="运行次数")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="floorplan 输出目录（自动生成前缀）")
    parser.add_argument("--log_file", type=str, default=None,
                        help="完整日志文件路径（原始输出）")
    parser.add_argument("--seed_file", type=str, default=None,
                        help="种子文件路径")
    parser.add_argument("--results_csv", type=str, default=None,
                        help="结果表格 CSV 文件路径")
    parser.add_argument("--skip_make", action="store_true",
                        help="跳过 make 编译步骤")
    parser.add_argument("--record_curve", action="store_true",
                        help="记录模拟退火过程中的详细参数曲线")
    parser.add_argument("-a","--algo", type=int, default=0,
                        help="算法模式: 0=原始算法, 1=GMS, 2=... (默认0)")
    parser.add_argument("--tune", type=str, default=None,
                        help="调优配置文件（YAML），对某个参数进行网格搜索。例如: --tune tune_config.yaml")
    return parser.parse_args()

# ---------- 辅助函数 ----------
def get_script_dir() -> Path:
    """返回脚本所在目录"""
    return Path(__file__).resolve().parent

def ensure_dir(path: Path) -> None:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)

def run_make(script_dir: Path) -> None:
    """执行 make -f Makefile.debug"""
    print("正在编译...")
    try:
        subprocess.run(["make", "-f", "Makefile.debug"], cwd=script_dir, check=True)
        print("编译完成。")
    except subprocess.CalledProcessError as e:
        print(f"编译失败: {e}", file=sys.stderr)
        sys.exit(1)

def generate_seeds(num_runs: int) -> List[int]:
    """生成随机种子列表，模拟 bash 的 $(( ($RANDOM << 15) + $RANDOM ))"""
    seeds = []
    for _ in range(num_runs):
        low = random.randint(0, 32767)
        high = random.randint(0, 32767)
        seed = (high << 15) + low
        seeds.append(seed)
    return seeds

def compute_five_number_summary(values):
    """
    计算五数汇总（剔除 IQR 异常值后）。
    返回 (min, q1, median, q3, max, 剔除个数)
    若数据不足则对应值为 None。
    """
    if not values or len(values) < 2:
        return None, None, None, None, None, 0
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def percentile(data, p):
        """线性插值百分位数"""
        k = (len(data) - 1) * p / 100.0
        f = int(k)
        c = k - f
        return data[f] * (1 - c) + data[min(f + 1, len(data) - 1)] * c

    q1 = percentile(sorted_vals, 25)
    q3 = percentile(sorted_vals, 75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    # 剔除异常值
    filtered = [v for v in sorted_vals if lower <= v <= upper]
    n_removed = len(sorted_vals) - len(filtered)

    if not filtered:
        return None, None, None, None, None, n_removed

    fmin = min(filtered)
    fmax = max(filtered)
    fq1 = percentile(filtered, 25)
    fmed = percentile(filtered, 50)
    fq3 = percentile(filtered, 75)
    return fmin, fq1, fmed, fq3, fmax, n_removed

def extract_last(pattern: str, output_text: str):
    matches = re.findall(pattern, output_text)
    if not matches:
        return None
    return matches[-1]

def parse_output(output_text: str) -> Dict[str, Optional[float]]:
    """
    从程序输出中提取指标，包括耗时和可行解状态。
    返回字典：
        - 数值指标：Width, Height, Area, Wirelength, R, Cost,
                     BTree_T_us, SA_T_s
        - 可行解标记：Feasible (1=找到可行解, 0=未找到)
    """
    # 数值提取模式
    patterns = {
        "Width": r"Width:\s+(\d+)",
        "Height": r"Height:\s+(\d+)",
        "Area": r"Area:\s+(\d+)",
        "Wirelength": r"Wirelength:\s+(\d+)",
        "R": r"R:\s+([0-9.]+)",
        "Cost": r"Cost:\s+([0-9.]+)",
        "BTree_T_us": r"\[BuildInitBtree\] 耗时:\s+(\d+)\s*us",
        "SA_T_s": r"\[SimulatedAnnealing\] 耗时:\s+([0-9.]+)\s*s",
    }
    
    result = {}
    for key, pat in patterns.items():
        val = extract_last(pat, output_text)
        if val is None:
            result[key] = None
            continue
        if key in ["BTree_T_us", "SA_T_s"]:
            result[key] = float(val)
        elif '.' in val:
            result[key] = float(val)
        else:
            result[key] = int(val)

    # 检测可行解：出现 "Not Found feasible solution" 则标记为 0，否则为 1
    if re.search(r"Not Found feasible solution", output_text):
        result["Feasible"] = 0
    else:
        result["Feasible"] = 1

    return result

def run_single(exec_path: Path, hardblocks: str, nets: str, terminals: str,
               floorplan_file: Path, ratio: float, seed: int, algo:int = 0, curve:bool = False) -> Tuple[str, Dict[str, Optional[float]], int]:
    """
    运行n次实验，返回 (原始输出, 提取的指标字典, 返回码)
    """
    cmd = [str(exec_path), "--algo", str(algo)]
    if curve:
        cmd.append("--curve")
    cmd.extend([hardblocks, nets, terminals, str(floorplan_file), str(ratio), str(seed)])
    
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = proc.stdout + proc.stderr
        metrics = parse_output(output)
        return output, metrics, proc.returncode
    except Exception as e:
        error_output = f"运行失败: {e}\n"
        return error_output, {}, -1

def run_single_with_config(exec_path: Path, hardblocks: str, nets: str, terminals: str,
                           floorplan_file: Path, ratio: float, seed: int,
                           algo: int = 0, config_file: Optional[str] = None,
                           curve: bool = False) -> Tuple[str, Dict[str, Optional[float]], int]:
    """
    与 run_single 类似，但额外支持 --config 参数传入临时 JSON 配置文件。
    """
    cmd = [str(exec_path), "--algo", str(algo)]
    if config_file:
        cmd.extend(["--config", config_file])
    if curve:
        cmd.append("--curve")
    cmd.extend([hardblocks, nets, terminals, str(floorplan_file), str(ratio), str(seed)])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = proc.stdout + proc.stderr
        metrics = parse_output(output)
        return output, metrics, proc.returncode
    except Exception as e:
        error_output = f"运行失败: {e}\n"
        return error_output, {}, -1

def run_with_curve_logging(exec_path, hardblocks, nets, terminals, floorplan_file,
                           ratio, seed, curve_csv_path, log_file_path, algo=0, curve:bool = False):
    """
    要求 C++ 程序支持 --curve 选项。
    运行n次实验，实时过滤输出：
    - 以 'CSV:' 开头的行：去掉前缀后写入 curve_csv_path
    - 其他行：追加到 log_file_path，并收集到 full_output 用于最终解析
    返回 (full_output, metrics, returncode)
    """
    cmd = [str(exec_path), "--algo", str(algo)]
    if curve:
        cmd.append("--curve")
    cmd.extend([hardblocks, nets, terminals, str(floorplan_file), str(ratio), str(seed)])
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)  # 行缓冲

    # 打开曲线 CSV 文件，写入表头
    with open(curve_csv_path, 'w', newline='') as curve_f:
        # 根据 C++ 输出字段顺序定义表头（请与 C++ 代码中的输出顺序严格一致）
        header = "width,height,area,wirelength,R,cost,Total_Moves,T_Moves,T_uphill,T_reject,T"
        curve_f.write(header + '\n')

        # 收集非 CSV 行（用于最终解析）
        full_output_lines = []
        
        # 逐行读取
        for line in proc.stdout:
            if line.startswith("CSV:"):
                # CSV 数据：去掉前缀，写入曲线文件
                curve_f.write(line[4:].lstrip())  # line 已包含换行符
            else:
                # 非 CSV 行：写入日志文件，同时收集
                full_output_lines.append(line)
                with open(log_file_path, "a") as log_f:
                    log_f.write(line)

        proc.wait()
        returncode = proc.returncode

    # 将收集的非 CSV 行合并为完整输出，用于解析最终指标
    full_output = ''.join(full_output_lines)
    metrics = parse_output(full_output)   # 复用原有的 parse_output 函数
    return full_output, metrics, returncode

# ========== 调优相关 ==========

ALGO_TO_BLOCK = {
    0: "SA",
    1: "GMS",
    2: "FastSA",
    3: "GMS_FastSA",
    4: "SawTooth_FastSA",
    5: "GMS_DoubleMatrix",
    6: "GMS_SawTooth_FastSA",
}

# ========== 公共统计输出函数（减少 main 和 run_tuning 的代码重复） ==========

def compute_stats_from_table(table_data):
    """
    从 table_data（每行格式：[run, seed, Width, Height, Area, Wirelength, R, Cost, BTree_T_us, SA_T_s, Feasible]）
    计算统计量，返回 (stats_dict, five_stats_dict, found_count, not_found_count)
    """
    stats = {}
    five_stats = {}
    col_names = ["Width", "Height", "Area", "Wirelength", "R", "Cost",
                  "BTree_T_us", "SA_T_s", "Feasible"]

    for col_idx, col_name in enumerate(col_names, start=2):
        values = [row[col_idx] for row in table_data if row[col_idx] is not None]
        if values:
            mean_val = statistics.mean(values)
            variance_val = statistics.stdev(values) if len(values) > 1 else 0.0
            stats[col_name] = (mean_val, variance_val)
        else:
            stats[col_name] = (None, None)
        five_stats[col_name] = compute_five_number_summary(values)

    # 可行解统计
    feasible_vals = [row[-1] for row in table_data if row[-1] is not None]
    if feasible_vals:
        found_count = sum(feasible_vals)
        not_found_count = len(feasible_vals) - found_count
    else:
        found_count = not_found_count = None

    return stats, five_stats, found_count, not_found_count


def write_statistics_to_log(log_file, table_data, algo, mode_desc="", extra_lines=None):
    """将统计结果写入日志文件（与 main() 中原有格式一致）"""
    stats, five_stats, found_count, not_found_count = compute_stats_from_table(table_data)

    with open(log_file, "a") as lf:
        lf.write(f"\n{'='*60}\n")
        lf.write(f"最终结果 ({mode_desc})\n")
        lf.write(f"{'='*60}\n")
        if extra_lines:
            for line in extra_lines:
                lf.write(line + "\n")
        lf.write("统计汇总（剔除 IQR 异常值后）\n")
        header = (f"{'指标':<11}{'平均值':<14}{'标准差':<13}{'最小值':<11}{'Q1':<13}"
                  f"{'中位数':<11}{'Q3':<12}{'最大值':<11}{'剔除':<6}")
        lf.write(header + "\n")
        lf.write("-" * 116 + "\n")
        for name, (mean_val, var_val) in stats.items():
            fmin, fq1, fmed, fq3, fmax, n_rem = five_stats.get(name, (None,) * 6)
            if mean_val is not None:
                lf.write(f"{name:<12} {mean_val:<15.4f} {var_val:<15.4f} "
                         f"{f'{fmin:.4f}' if fmin is not None else '-':<12} "
                         f"{f'{fq1:.4f}' if fq1 is not None else '-':<12} "
                         f"{f'{fmed:.4f}' if fmed is not None else '-':<12} "
                         f"{f'{fq3:.4f}' if fq3 is not None else '-':<12} "
                         f"{f'{fmax:.4f}' if fmax is not None else '-':<12} {n_rem:<6}\n")
            else:
                lf.write(f"{name:<12} {'无有效数据':<15} {'无有效数据':<15}\n")
        lf.write(f"算法模式：{algo}\n")
        if found_count is not None:
            lf.write(f"可行解统计: found = {found_count}, not found = {not_found_count}\n")
        lf.write(f"结束时间: {datetime.now().strftime('%c')}\n")


def print_statistics_to_console(table_data, algo):
    """将统计结果打印到控制台（与 main() 中原有格式一致）"""
    stats, five_stats, found_count, not_found_count = compute_stats_from_table(table_data)

    print("\n========== 统计结果 ==========")
    header = f"{'指标':<11}{'平均值':<13}{'标准差':<13}{'最小值':<10}{'Q1':<13}{'中位数':<10}{'Q3':<13}{'最大值':<12}"
    print(header)
    print("-" * 105)
    for name, (mean_val, var_val) in stats.items():
        fmin, fq1, fmed, fq3, fmax, n_rem = five_stats.get(name, (None,) * 6)
        if mean_val is not None:
            print(f"{name:<12} {mean_val:<15.4f} {var_val:<15.4f} "
                  f"{f'{fmin:.4f}' if fmin is not None else '-':<12} "
                  f"{f'{fq1:.4f}' if fq1 is not None else '-':<12} "
                  f"{f'{fmed:.4f}' if fmed is not None else '-':<12} "
                  f"{f'{fq3:.4f}' if fq3 is not None else '-':<12} "
                  f"{f'{fmax:.4f}' if fmax is not None else '-':<12}")
        else:
            print(f"{name:<12} {'无有效数据':<15} {'无有效数据':<15}")
    print(f"算法模式：{algo}")
    if found_count is not None:
        print(f"可行解统计: found = {found_count}, not found = {not_found_count}")

# ========== 种子管理函数 ==========

def load_or_generate_seeds(num_runs: int, seed_file_arg: Optional[str],
                           script_dir: Path, algo_tag: str,
                           timestamp: str) -> List[int]:
    """
    统一处理种子逻辑：
    - 如果 seed_file_arg 存在且文件可读，读取之
    - 否则生成 num_runs 个随机种子并保存到默认路径
    返回种子列表
    """
    if seed_file_arg is not None:
        seed_path = Path(seed_file_arg).resolve()
        if seed_path.exists():
            print(f"读取种子文件: {seed_path}")
            with open(seed_path, "r") as sf:
                seeds = [int(line.strip()) for line in sf if line.strip()]
            if len(seeds) != num_runs:
                print(f"警告: 种子文件中的种子数量 ({len(seeds)}) 与实验次数 ({num_runs}) 不匹配，"
                      f"将使用文件中的前 {num_runs} 个种子")
                seeds = seeds[:num_runs]
            while len(seeds) < num_runs:
                seeds.append(random.randint(0, 2**30 - 1))
                print(f"补充种子: {seeds[-1]}")
            return seeds
        else:
            print(f"种子文件不存在，生成 {num_runs} 个随机种子并保存到 {seed_path}")
            seeds = generate_seeds(num_runs)
            seed_path.parent.mkdir(parents=True, exist_ok=True)
            with open(seed_path, "w") as sf:
                for s in seeds:
                    sf.write(f"{s}\n")
            return seeds
    else:
        seed_file = script_dir / f"./seeds/seeds_{num_runs}{algo_tag}_{timestamp}.txt"
        print(f"生成 {num_runs} 个随机种子...")
        seeds = generate_seeds(num_runs)
        seed_file.parent.mkdir(parents=True, exist_ok=True)
        with open(seed_file, "w") as sf:
            for s in seeds:
                sf.write(f"{s}\n")
        print(f"种子已保存到 {seed_file}")
        return seeds


# ========== 编译与路径管理 ==========

def compile_and_check(exec_path: Path, script_dir: Path, skip_make: bool) -> None:
    """编译（如需）并检查可执行文件是否存在"""
    if not skip_make:
        cpp_src_dir = script_dir / "cpp_src"
        if not cpp_src_dir.exists():
            print(f"错误: cpp_src 目录不存在: {cpp_src_dir}", file=sys.stderr)
            sys.exit(1)
        run_make(cpp_src_dir)
    if not exec_path.exists():
        print(f"错误: 可执行文件不存在: {exec_path}", file=sys.stderr)
        sys.exit(1)


def resolve_output_dir(script_dir: Path, args) -> Path:
    """解析输出目录路径"""
    if args.output_dir is None:
        match = re.search(r'(\d+)', args.hardblocks)
        num_blocks = match.group(1) if match else "unknown"
        ratio_str = str(args.white_space_ratio).replace('.', '_')
        output_dir = (script_dir / f"./output/test_{num_blocks}blocks_ratio_"
                      f"{ratio_str}_total_{args.num_runs}_algo{args.algo}")
    else:
        output_dir = Path(args.output_dir)
    output_dir = output_dir.resolve()
    ensure_dir(output_dir)
    return output_dir


def resolve_log_file(script_dir: Path, args, timestamp: str) -> Path:
    """解析日志文件路径"""
    if args.log_file is None:
        log_file = script_dir / f"./log/running_results_algo{args.algo}_{timestamp}.txt"
    else:
        log_file = Path(args.log_file)
    log_file = log_file.resolve()
    ensure_dir(log_file.parent)
    return log_file


def write_log_header(log_file: Path, hardblocks: str, nets: str, terminals: str,
                     ratio: float, num_runs: int) -> None:
    """写入实验头部信息到日志文件"""
    with open(log_file, "w") as lf:
        lf.write("=" * 46 + "\n")
        lf.write("Batch floorplanning experiment\n")
        lf.write(f"Hardblocks: {hardblocks}\n")
        lf.write(f"Nets:       {nets}\n")
        lf.write(f"Terminals:  {terminals}\n")
        lf.write(f"Ratio:      {ratio}\n")
        lf.write(f"Runs:       {num_runs}\n")
        lf.write(f"Start time: {datetime.now().strftime('%c')}\n")
        lf.write("=" * 46 + "\n\n")


def resolve_common_paths(script_dir: Path, args) -> Tuple[Path, str, str, str]:
    """解析可执行文件和测试文件路径（exec, hardblocks, nets, terminals）"""
    exec_path = (script_dir / args.executable).resolve()
    hardblocks = str((script_dir / args.hardblocks).resolve())
    nets = str((script_dir / args.nets).resolve())
    terminals = str((script_dir / args.terminals).resolve())
    return exec_path, hardblocks, nets, terminals

def run_tuning(args):
    """参数调优主逻辑"""
    if yaml is None:
        print("错误: 需要安装 PyYAML。请运行: pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    # ========== 1. 加载 YAML ==========
    tune_path = Path(args.tune)
    if not tune_path.exists():
        print(f"错误: 配置文件不存在: {tune_path}", file=sys.stderr)
        sys.exit(1)
    with open(tune_path) as f:
        tune = yaml.safe_load(f)

    algo = tune.get("algo", 0)
    raw_param = tune["parameter"]
    start = tune["start"]
    end = tune["end"]
    step = tune["step"]
    fixed_params = tune.get("fixed", {})

    # 修复4：支持 YAML 中 num_runs_per_value 和 num_runs 两种写法
    num_runs_per_value = tune.get("num_runs_per_value") or tune.get("num_runs", 5)

    # 修复5：剥离参数名中的块名前缀（如 "SA.k" → "k"）
    block_name = ALGO_TO_BLOCK.get(algo, "SA")
    prefix = block_name + "."
    if raw_param.startswith(prefix):
        param_name = raw_param[len(prefix):]
    else:
        param_name = raw_param

    # 曲线模式强制约束
    if args.record_curve:
        print("曲线调优模式: 强制 num_runs=1, 限制最多 10 个参数值")
        num_runs_per_value = 1

    # ========== 2. 生成参数值列表 ==========
    num_steps = int(round((end - start) / step)) + 1
    param_values = [round(start + i * step, 10) for i in range(num_steps)]
    if param_values[-1] != end:
        param_values.append(end)
    param_values = sorted(set(param_values))

    # 曲线模式限制最多 10 个参数值
    if args.record_curve and len(param_values) > 10:
        print(f"曲线模式限制: 参数值从 {len(param_values)} 个裁剪到 10 个")
        indices = [int(i * (len(param_values) - 1) / 9) for i in range(10)]
        param_values = [param_values[i] for i in sorted(set(indices))]

    # ========== 3. 准备路径 ==========
    script_dir = get_script_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    algo_tag = f"_algo{algo}"
    ratio_str = str(args.white_space_ratio).replace('.', '_')

    exec_path, hardblocks, nets, terminals = resolve_common_paths(script_dir, args)
    compile_and_check(exec_path, script_dir, args.skip_make)

    # --- 目录结构 ---
    # ./log/tune_algo0_r_2026-06-08_16:21:22/
    #     param_r0.5/
    #         running_results_algo0_r0.5.txt   (含完整统计)
    #     param_r0.55/
    #         running_results_algo0_r0.55.txt
    #     summary.txt                          (整体汇总)
    tune_log_root = script_dir / f"./log/tune{algo_tag}_{param_name}_{timestamp}"
    ensure_dir(tune_log_root)

    output_dir = script_dir / f"./output/tune{algo_tag}_{param_name}_{timestamp}"
    ensure_dir(output_dir)

    config_dir = script_dir / "./config"
    ensure_dir(config_dir)

    if args.record_curve:
        curve_root = (script_dir / "results" / "curve_results"
                      / f"tune{algo_tag}_{param_name}_{timestamp}")
        ensure_dir(curve_root)

    # ========== 4. 生成种子 ==========
    seeds = load_or_generate_seeds(num_runs_per_value, args.seed_file,
                                   script_dir, algo_tag, timestamp)

    # ========== 5. 打印概要 ==========
    print(f"\n{'='*70}")
    print(f"参数调优模式")
    print(f"算法模式:    {algo} ({block_name})")
    print(f"调优参数:    {param_name}")
    print(f"范围:        [{start}, {end}], 步长 {step} → {len(param_values)} 个值")
    print(f"每值运行:    {num_runs_per_value} 次")
    print(f"日志目录:    {tune_log_root}")
    print(f"{'='*70}\n")

    # 存储所有参数值的结果（用于最后的汇总表格）
    all_summary: Dict[float, Dict] = {}

    # ========== 6. 调优主循环 ==========
    for pv_idx, param_val in enumerate(param_values, start=1):
        val_str = str(param_val).replace('.', '_')
        folder_name = f"param_{param_name}{val_str}"
        param_log_dir = tune_log_root / folder_name
        ensure_dir(param_log_dir)

        log_file = param_log_dir / f"running_results{algo_tag}_{param_name}{val_str}.txt"
        curve_csv_path = None
        if args.record_curve:
            curve_csv_path = curve_root / folder_name / "curve_data.csv"
            ensure_dir(curve_csv_path.parent)

        param_table_data = []
        param_mode_desc = f"调优 {block_name}.{param_name}={param_val}"

        print(f"[{pv_idx}/{len(param_values)}] {param_name} = {param_val}")

        # 创建 JSON 配置文件
        config_dict = {block_name: {param_name: param_val, **fixed_params}}
        config_json_path = config_dir / f"tune{algo_tag}_{param_name}{val_str}.json"
        with open(config_json_path, "w") as f:
            json.dump(config_dict, f, indent=2)

        for run_idx, seed in enumerate(seeds, start=1):
            floorplan_file = output_dir / f"val{pv_idx}_run{run_idx}.floorplan"

            if args.record_curve:
                print(f"  运行 {run_idx}/{num_runs_per_value} (seed={seed}, 曲线)...", end=" ")
                output_text, metrics, retcode = run_single_with_config(
                    exec_path, hardblocks, nets, terminals,
                    floorplan_file, args.white_space_ratio, seed,
                    algo=algo, config_file=str(config_json_path), curve=True
                )
                # 过滤 CSV 行写入曲线文件
                curve_lines = []
                clean_lines = []
                for line in output_text.splitlines(True):
                    if line.startswith("CSV:"):
                        curve_lines.append(line[4:].lstrip())
                    else:
                        clean_lines.append(line)
                with open(curve_csv_path, 'w') as cf:
                    cf.write("width,height,area,wirelength,R,cost,Total_Moves,"
                             "T_Moves,T_uphill,T_reject,T\n")
                    cf.writelines(curve_lines)
                metrics = parse_output(''.join(clean_lines))
            else:
                print(f"  运行 {run_idx}/{num_runs_per_value} (seed={seed})...", end=" ")
                output_text, metrics, retcode = run_single_with_config(
                    exec_path, hardblocks, nets, terminals,
                    floorplan_file, args.white_space_ratio, seed,
                    algo=algo, config_file=str(config_json_path), curve=False
                )

            # 写原始日志
            with open(log_file, "a") as lf:
                lf.write("=" * 60 + "\n")
                lf.write(f"Run {run_idx}/{num_runs_per_value} (seed={seed})\n")
                lf.write("=" * 60 + "\n")
                lf.write(output_text)
                if retcode != 0:
                    lf.write(f"[警告] 返回码: {retcode}\n")
                lf.write("\n")

            row = [
                run_idx, seed,
                metrics.get("Width"), metrics.get("Height"),
                metrics.get("Area"), metrics.get("Wirelength"),
                metrics.get("R"), metrics.get("Cost"),
                metrics.get("BTree_T_us"), metrics.get("SA_T_s"),
                metrics.get("Feasible")
            ]
            param_table_data.append(row)

            cost_str = f"{metrics.get('Cost', 'N/A')}"
            feas_str = "✓" if metrics.get("Feasible") else "✗"
            print(f"Cost={cost_str} {feas_str}")

        # --- 写当前参数值的统计结果到各自的 log 文件 ---
        write_statistics_to_log(log_file, param_table_data, algo,
                                mode_desc=param_mode_desc)

        # 保存汇总信息
        stats, _, found_cnt, _ = compute_stats_from_table(param_table_data)
        cost_mean = stats.get("Cost", (None, None))[0]
        feas_rate = (found_cnt / num_runs_per_value * 100) if found_cnt is not None else 0
        all_summary[param_val] = {"mean_cost": cost_mean, "feas_rate": feas_rate}

        print(f"  → 平均 Cost={cost_mean:.4f}, 可行解率={feas_rate:.0f}%")

    # ========== 7. 整体汇总表格 ==========
    print(f"\n{'='*70}")
    print(f"调优汇总 ({block_name}.{param_name})")
    print(f"{'='*70}")
    header = f"{'参数值':<12}{'平均Cost':<14}{'可行解率':<12}"
    print(header)
    print("-" * 50)

    summary_file = tune_log_root / "summary.txt"
    with open(summary_file, "w") as sf:
        sf.write("调优汇总\n")
        sf.write(f"算法: {algo} ({block_name}), 参数: {param_name}\n")
        sf.write(f"范围: [{start}, {end}], 步长: {step}, 每值运行: {num_runs_per_value} 次\n")
        sf.write(f"时间: {timestamp}\n")
        sf.write(header + "\n")
        sf.write("-" * 50 + "\n")

        for pv in sorted(all_summary.keys()):
            info = all_summary[pv]
            mc = info["mean_cost"]
            fr = info["feas_rate"]
            mc_str = f"{mc:.4f}" if mc is not None else "N/A"
            line = f"{pv:<12.6f} {mc_str:<14} {fr:<10.1f}%"
            print(line)
            sf.write(line + "\n")

    # ========== 8. 清理临时 JSON 配置文件 ==========
    import glob
    for f in glob.glob(str(config_dir / f"tune{algo_tag}_{param_name}_*.json")):
        try:
            os.unlink(f)
        except OSError:
            pass
    print(f"已清理临时配置文件 ({config_dir}/)")

    print(f"\n详细日志: {tune_log_root}/")
    print(f"汇总文件: {summary_file}")
    print("调优完成。")

# ---------- 主函数 ----------
def main():
    args = parse_args()
    
    # ===== 新增：调优模式 =====
    if args.tune:
        run_tuning(args)
        return
    # ==========================
    
    script_dir = get_script_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")    #时间戳
    algo_tag = f"_algo{args.algo}"                              #算法标识

    if args.record_curve:
        print(f"曲线模式运行已开启，请注意剩余存储容量！")
        if (args.num_runs > 10):
            args.num_runs = 10  #设置运行次数上限
        

    # 补全默认路径（相对于脚本目录）
    exec_path, hardblocks, nets, terminals = resolve_common_paths(script_dir, args)

    # 输出目录
    output_dir = resolve_output_dir(script_dir, args)

    # 日志文件（原始输出）
    log_file = resolve_log_file(script_dir, args, timestamp)

    # 结果 CSV 文件
    # if args.results_csv is None:
    #     results_csv = script_dir / f"./results/n_runs_result/results_{args.num_runs}{algo_tag}_{timestamp}.csv"
    # else:
    #     results_csv = Path(args.results_csv)
    # results_csv = results_csv.resolve()
    # ensure_dir(results_csv.parent)

    # 编译
    compile_and_check(exec_path, script_dir, args.skip_make)

    # 生成种子
    # 生成或读取种子列表
    seeds = load_or_generate_seeds(args.num_runs, args.seed_file, script_dir, algo_tag, timestamp)

    # 准备日志文件（写入头部）
    write_log_header(log_file, hardblocks, nets, terminals, args.white_space_ratio, args.num_runs)

    # 用于存储表格数据
    table_data = []   # 每个元素为 (run, seed, width, height, area, wirelength, R, cost)

    print(f"开始批量测试，日志保存到 {log_file}")
    # print(f"结果表格将保存到 {results_csv}")

    # 批量运行（原逻辑）
    if args.record_curve:
        # 曲线模式：可运行多次，使用特殊处理函数
        print("\n曲线记录模式已开启，将运行多次实验并分别保存曲线数据。\n")

        # 曲线结果目录，不存在就创建
        curve_results_dir = script_dir / "results" / "curve_results" / f"curve_data{algo_tag}_{timestamp}{algo_tag}"
        ensure_dir(curve_results_dir)
        
        for run_idx, seed in enumerate(seeds, start=1):
            floorplan_file = output_dir / f"run{run_idx}_{timestamp}.floorplan"
            # 生成曲线 CSV 文件路径（默认放在 output_dir 下，也可自定义）
            curve_csv_path = curve_results_dir / f"curve_data_run{run_idx}{algo_tag}.csv"
            print(f"[{run_idx}/{args.num_runs}] 运行中 (曲线记录)...")
            output_text, metrics, retcode = run_with_curve_logging(
                exec_path, hardblocks, nets, terminals,
                floorplan_file, args.white_space_ratio, 
                seed, curve_csv_path, log_file, algo=args.algo, 
                curve=args.record_curve   # 新增
            )
            # 仍然可以收集最终指标到 table_data，以便统计（可选）
            # 提取指标存入表格
            row = [
                run_idx, seed,
                metrics.get("Width"),
                metrics.get("Height"),
                metrics.get("Area"),
                metrics.get("Wirelength"),
                metrics.get("R"),
                metrics.get("Cost"),
                metrics.get("BTree_T_us"),
                metrics.get("SA_T_s"),
                metrics.get("Feasible"),   # 添加可行解标记
            ]
            table_data.append(row)
            
            # 终端显示进度
            print(f"[{run_idx}/{args.num_runs}] seed={seed} 完成 (返回码 {retcode})")

            # 附加统计信息到日志文件末尾

            with open(log_file, "a") as lf:
                lf.write(f"\n{'Run: ':<12}{run_idx}")
                lf.write(f"\n{'曲线数据已保存至: ':<12}{curve_csv_path}")
                lf.write(f"\n结束时间: {datetime.now().strftime('%c')}\n")
                lf.write("=" * 46 + "\n\n")

    else:
        # 原批量运行逻辑（不变）
        # 批量运行
        for run_idx, seed in enumerate(seeds, start=1):
            floorplan_file = output_dir / f"run{run_idx}_{timestamp}.floorplan"
            print(f"[{run_idx}/{args.num_runs}] seed={seed} 运行中...")

            output_text, metrics, retcode = run_single(
                exec_path, hardblocks, nets, terminals,
                floorplan_file, args.white_space_ratio, 
                seed, algo=args.algo, curve=False   # 批量模式下不输出曲线
            )

            # 记录原始输出到日志
            with open(log_file, "a") as lf:
                lf.write("=" * 60 + "\n")
                lf.write(f" Run {run_idx} / {args.num_runs}  (seed = {seed})\n")
                lf.write("=" * 60 + "\n")
                lf.write(output_text)
                if retcode != 0:
                    lf.write(f"\n[警告] 程序返回非零退出码: {retcode}\n")
                lf.write("\n")

            # 提取指标存入表格
            row = [
                run_idx, seed,
                metrics.get("Width"),
                metrics.get("Height"),
                metrics.get("Area"),
                metrics.get("Wirelength"),
                metrics.get("R"),
                metrics.get("Cost"),
                metrics.get("BTree_T_us"),
                metrics.get("SA_T_s"),
                metrics.get("Feasible"),   # 添加可行解标记
            ]
            table_data.append(row)

            # 终端显示进度
            print(f"[{run_idx}/{args.num_runs}] seed={seed} 完成 (返回码 {retcode})")

    # 写入 CSV 表格
    # with open(results_csv, "w", newline="") as csvfile:
    #     writer = csv.writer(csvfile)
    #     writer.writerow([
    #         "run", "seed", "Width", "Height", "Area", "Wirelength", "R", "Cost",
    #         "BTree_T_us", "SA_T_s", "Feasible"
    #     ])
    #     for row in table_data:
    #         writer.writerow(row)

    # print(f"\n结果表格已保存到 {results_csv}")
    
    # ---- 统计输出 ----
    print_statistics_to_console(table_data, args.algo)
    write_statistics_to_log(log_file, table_data, args.algo,
                            mode_desc="曲线模式" if args.record_curve else "批量实验模式")

    print(f"\n完整日志保存在: {log_file}")
    print("全部完成。")

if __name__ == "__main__":
    main()