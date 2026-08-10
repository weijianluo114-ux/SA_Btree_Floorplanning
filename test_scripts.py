#!/usr/bin/env python3
"""
批量运行 floorplan 实验，记录指标并计算统计信息。
用法示例:
    python run_experiments.py --num-runs 100 --white-space-ratio 0.1
"""
import importlib.util
from argparse import Namespace
import argparse
import subprocess
import sys
import random
import re
import json
import yaml
from pathlib import Path
from datetime import datetime
import statistics
from typing import Dict, List, Optional, Tuple

# ---------- 辅助函数 ----------
def get_script_dir() -> Path:
    """返回脚本所在目录"""
    return Path(__file__).resolve().parent

def _load_scripts_module(module_name: str):
    """从 scripts/ 目录加载绘图脚本模块（懒加载，避免强制引入 matplotlib/pandas）"""
    scripts_dir = get_script_dir() / "scripts"
    file_path = scripts_dir / f"{module_name}.py"
    if not file_path.exists():
        print(f"错误: 找不到绘图脚本 {file_path}", file=sys.stderr)
        sys.exit(1)
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

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
        "SA_T_s": r"\[SimulatedAnnealing\] 耗时:\s+([0-9.]+)\s*(ms|s)",
    }
    
    result = {}
    for key, pat in patterns.items():
        val = extract_last(pat, output_text)
        if val is None:
            result[key] = None
            continue
        if key == "BTree_T_us":
            result[key] = float(val)
        elif key == 'SA_T_s':
            value = float(val[0]) if isinstance(val, tuple) else float(val)
            unit = val[1] if isinstance(val, tuple) else 's'
            result[key] = value / 1000.0 if unit == 'ms' else value
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
    运行单次实验（无临时配置），返回 (原始输出, 提取的指标字典, 返回码)。
    等价于 run_single_with_config(config_file=None)，为保留旧调用点而保留的薄封装。
    """
    return run_single_with_config(
        exec_path, hardblocks, nets, terminals,
        floorplan_file, ratio, seed,
        algo=algo, config_file=None, curve=curve,
    )

def run_single_with_config(exec_path: Path, hardblocks: str, nets: str, terminals: str,
                           floorplan_file: Path, ratio: float, seed: int,
                           algo: int = 0, config_file: Optional[str] = None,
                           curve: bool = False) -> Tuple[str, Dict[str, Optional[float]], int]:
    """
    运行n次实验，返回 (原始输出, 提取的指标字典, 返回码)，额外支持 --config 参数传入临时 JSON 配置文件。
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
        # Feasible 单独处理：统计全部 run（反映真实成功率）
        if col_name == "Feasible":
            values = [row[col_idx] for row in table_data if row[col_idx] is not None]
        # values = [row[col_idx] for row in table_data if row[col_idx] is not None]
        # 改后：
        else:
            values = [row[col_idx] for row in table_data 
                    if row[col_idx] is not None and row[-1] == 1]
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
        lf.write(f"结束时间: {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}\n")


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
        lf.write(f"Start time: {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}\n")
        lf.write("=" * 46 + "\n\n")

def create_run_dirs(circuit: str, white_space_ratio: float,
                    algo: int, num_runs: int) -> Tuple[Path, Path]:
    """
    创建统一日志目录结构，返回 (run_dir, log_file)。
    
    目录结构：
        log/YYYY_MM_DD/HH-MM-SS_{circuit}_wsrXXX_a{algo}_tot{N}/
            ├── run.log
            ├── config.yaml
            ├── output/
            ├── figures/
            ├── curves/
            └── seeds/
    """
    now = datetime.now()
    date_str = now.strftime("%Y_%m_%d")
    time_str = now.strftime("%H-%M-%S")
    wsr_str = f"{int(white_space_ratio * 100):03d}"       # 0.1 → 010

    script_dir = get_script_dir()
    log_root = script_dir / "log"
    date_dir = log_root / date_str

    run_name = f"{time_str}_{circuit}_wsr{wsr_str}_a{algo}_tot{num_runs}"
    run_dir = date_dir / run_name

    # 创建所有子目录
    for sub in ["output", "figures", "curves", "seeds"]:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)

    log_file = run_dir / "run.log"
    return run_dir, log_file

def update_latest_link(run_dir: Path) -> None:
    """
    在 log/ 下创建 latest 符号链接，指向最近一次运行的实例目录。
    若符号链接不可用（如 Windows 无管理员权限），回退为 latest.txt。
    """
    log_root = run_dir.parent.parent          # run_dir = log/2026_08_09/xxx/, 上两级 = log/
    latest_link = log_root / "latest"

    # 删旧
    if latest_link.is_symlink() or latest_link.exists():
        latest_link.unlink()

    try:
        rel_path = run_dir.relative_to(log_root)
        latest_link.symlink_to(str(rel_path), target_is_directory=True)
    except OSError:
        # 回退：写入 latest.txt
        latest_txt = log_root / "latest.txt"
        latest_txt.write_text(str(run_dir.relative_to(log_root)), encoding="utf-8")
        print(f"注意: 无法创建符号链接，已回退为 {latest_txt}")

def write_config_yaml(run_dir: Path, args: Namespace) -> None:
    """将本次运行的关键参数写入 config.yaml，便于复现。"""
    config_path = run_dir / "config.yaml"
    content = {
        "circuit": args.circuit,
        "white_space_ratio": args.white_space_ratio,
        "algo": args.algo,
        "num_runs": args.num_runs,
        "executable": args.executable,
        "skip_make": args.skip_make,
        "record_curve": args.record_curve,
        "timestamp": datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
    }
    with open(config_path, "w") as f:
        yaml.dump(content, f, default_flow_style=False, allow_unicode=True)

def resolve_common_paths(script_dir: Path, args) -> Tuple[Path, str, str, str]:
    """解析可执行文件和测试文件路径(exec, hardblocks, nets, terminals)"""
    exec_path = (script_dir / args.executable).resolve()
    
    circuit = args.circuit or 'n10' # use args.circuit as first choich
    hardblocks = str((script_dir / f'./testcase/{circuit}.hardblocks').resolve())
    nets = str((script_dir / f'./testcase/{circuit}.nets').resolve())
    terminals = str((script_dir / f'./testcase/{circuit}.pl').resolve())
    return exec_path, hardblocks, nets, terminals

def _make_metric_row(run_idx, seed, metrics):
    """从单次运行指标构造统计表格的一行。"""
    return [
        run_idx, seed,
        metrics.get("Width"), metrics.get("Height"),
        metrics.get("Area"), metrics.get("Wirelength"),
        metrics.get("R"), metrics.get("Cost"),
        metrics.get("BTree_T_us"), metrics.get("SA_T_s"),
        metrics.get("Feasible"),
    ]

def run_tuning(args):
    """参数调优主逻辑"""
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

    # 曲线模式：num_runs_per_value 上限保护（>5 时警告并截断到 5；≤5 则维持 YAML 值）
    if args.record_curve and num_runs_per_value > 5:
        print(f"[警告] 曲线调优模式: num_runs_per_value={num_runs_per_value} 超过上限 5，已限制为 5")
        num_runs_per_value = 5

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
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    algo_tag = f"_algo{algo}"

    exec_path, hardblocks, nets, terminals = resolve_common_paths(script_dir, args)
    compile_and_check(exec_path, script_dir, args.skip_make)

    # --- 目录结构：log/YYYY_MM_DD/HH-MM-SS_tune_a{algo}_{param}_{start}-{end}/ ---
    #     param_{value}/
    #         running_results_algo{...}.txt     (含完整统计)
    #     output/                               (val{pv}_run{r}.floorplan)
    #     curves/                               (param_{value}/curve_data.csv)
    #     figures/                              (曲线图)
    #     seeds/                                (种子快照)
    #     summary.txt                           (整体汇总)
    now = datetime.now()
    date_str = now.strftime("%Y_%m_%d")
    time_str = now.strftime("%H-%M-%S")
    tune_name = f"{time_str}_tune_a{algo}_{param_name}_{start}-{end}"
    tune_log_root = script_dir / "log" / date_str / tune_name
    ensure_dir(tune_log_root)

    # 日志目录：tune_log/param_*/run{idx}.log + statistics.txt
    tune_log = tune_log_root / "tune_log"
    ensure_dir(tune_log)

    output_dir = tune_log_root / "output"
    ensure_dir(output_dir)

    figure_root = tune_log_root / "figures"
    ensure_dir(figure_root)

    seeds_root = tune_log_root / "seeds"
    ensure_dir(seeds_root)

    config_dir = script_dir / "./config"
    ensure_dir(config_dir)

    if args.record_curve:
        curve_root = tune_log_root / "curves"
        ensure_dir(curve_root)

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
        param_tag = f"{param_name}{val_str}"          # 如 "r0_8"
        folder_name = f"param_{param_tag}"            # 如 "param_r0_8"
        param_log_dir = tune_log / folder_name
        ensure_dir(param_log_dir)

        # 本参数聚合 log：tune_log/param_*/run.log（同一参数仅种子不同，合并为一个 log，类似单次 run.log）
        run_log_file = param_log_dir / "run.log"
        write_log_header(run_log_file, hardblocks, nets, terminals,
                         args.white_space_ratio, num_runs_per_value)

        # 本参数的输出目录与种子目录（按参数值分类）
        output_param_dir = output_dir / folder_name
        ensure_dir(output_param_dir)
        seeds_param_dir = seeds_root / folder_name
        ensure_dir(seeds_param_dir)

        # 每个参数值使用独立的种子集，保存到 seeds/param_*/
        seeds = load_or_generate_seeds(num_runs_per_value, args.seed_file,
                                       script_dir, algo_tag, timestamp)
        seed_snapshot = seeds_param_dir / f"seeds_{num_runs_per_value}{algo_tag}_{timestamp}.txt"
        with open(seed_snapshot, "w") as sf:
            for s in seeds:
                sf.write(f"{s}\n")

        param_table_data = []
        param_mode_desc = f"调优 {block_name}.{param_name}={param_val}"

        print(f"[{pv_idx}/{len(param_values)}] {param_name} = {param_val}")

        # 创建 JSON 配置文件
        config_dict = {block_name: {param_name: param_val, **fixed_params}}
        config_json_path = config_dir / f"tune{algo_tag}_{param_name}{val_str}.json"
        with open(config_json_path, "w") as f:
            json.dump(config_dict, f, indent=2)

        for run_idx, seed in enumerate(seeds, start=1):
            floorplan_file = output_param_dir / f"run{run_idx}.floorplan"

            if args.record_curve:
                print(f"  运行 {run_idx}/{num_runs_per_value} (seed={seed}, 曲线)...", end=" ")
                output_text, metrics, retcode = run_single_with_config(
                    exec_path, hardblocks, nets, terminals,
                    floorplan_file, args.white_space_ratio, seed,
                    algo=algo, config_file=str(config_json_path), curve=True
                )
                # 过滤 CSV 行：曲线写入 curves/param_*/run{idx}_curve_data.csv，log 移除 CSV 行
                curve_lines = []
                clean_lines = []
                for line in output_text.splitlines(True):
                    if line.startswith("CSV:"):
                        curve_lines.append(line[4:].lstrip())
                    else:
                        clean_lines.append(line)
                curve_csv_path = curve_root / folder_name / f"run{run_idx}_curve_data.csv"
                ensure_dir(curve_csv_path.parent)   # 确保 curves/param_*/ 目录存在
                with open(curve_csv_path, 'w') as cf:
                    cf.write("width,height,area,wirelength,R,cost,Total_Moves,"
                             "T_Moves,T_uphill,T_reject,T\n")
                    cf.writelines(curve_lines)
                log_output_text = ''.join(clean_lines)   # log 不含 CSV 行
                metrics = parse_output(log_output_text)
            else:
                print(f"  运行 {run_idx}/{num_runs_per_value} (seed={seed})...", end=" ")
                output_text, metrics, retcode = run_single_with_config(
                    exec_path, hardblocks, nets, terminals,
                    floorplan_file, args.white_space_ratio, seed,
                    algo=algo, config_file=str(config_json_path), curve=False
                )
                log_output_text = output_text

            # 追加当前 run 的输出到本参数 run.log（不含 CSV 行）
            with open(run_log_file, "a") as lf:
                lf.write("=" * 60 + "\n")
                lf.write(f" Run {run_idx} / {num_runs_per_value}  (seed = {seed})\n")
                lf.write("=" * 60 + "\n")
                lf.write(log_output_text)
                if retcode != 0:
                    lf.write(f"\n[警告] 返回码: {retcode}\n")
                lf.write("\n")

            row = _make_metric_row(run_idx, seed, metrics)
            param_table_data.append(row)

            cost_str = f"{metrics.get('Cost', 'N/A')}"
            feas_str = "✓" if metrics.get("Feasible") else "✗"
            print(f"Cost={cost_str} {feas_str}")

        # --- 写当前参数值的统计结果（追加到本参数 run.log 末尾，类似批量模式） ---
        write_statistics_to_log(run_log_file, param_table_data, algo,
                                mode_desc=param_mode_desc)

        # 保存汇总信息
        stats, _, found_cnt, _ = compute_stats_from_table(param_table_data)
        cost_mean = stats.get("Cost", (None, None))[0]
        feas_rate = (found_cnt / num_runs_per_value * 100) if found_cnt is not None else 0
        all_summary[param_val] = {"mean_cost": cost_mean, "feas_rate": feas_rate}

        cost_str = f"{cost_mean:.4f}" if cost_mean is not None else "N/A"
        print(f"  → 平均 Cost={cost_str}, 可行解率={feas_rate:.0f}%")

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
    for f in config_dir.glob("tune_*.json"):
        try:
            f.unlink()
        except OSError:
            pass
    print(f"已清理临时配置文件 ({config_dir}/)")

    # ===== 更新 latest 链接 =====
    update_latest_link(tune_log_root)

    # ===== 可选：绘制 floorplan / B*-tree（调优模式）=====
    if args.draw_fp:
        draw_fp = _load_scripts_module("draw_fixed_outline")
        tune_fp_args = Namespace(
            tune=str(tune_log_root),               # 调优运行目录
            output=str(figure_root),               # 图片输出到 tune_dir/figures/
            dpi=args.fp_dpi,
            algo=algo,
            max_read=None,
            blocks=int(args.circuit.lstrip('n')),  # 备用块数（通常由 floorplan 推断）
        )
        draw_fp.main(tune_fp_args)

    print(f"\n详细日志: {tune_log_root}/")
    print(f"汇总文件: {summary_file}")
    print("调优完成。")

# ---------- 参数解析 ----------
def parse_args():
    parser = argparse.ArgumentParser(description="批量运行 hw3_dbg 并收集结果")
    parser.add_argument("--executable", type=str, default="./bin/hw3_dbg",
                        help="可执行文件路径（相对于脚本位置）")
    parser.add_argument("--circuit", type=str, default="n10", choices=['n10', 'n30', 'n50', 'n100', 'n200', 'n300'],
                        help="auto-load ./testcase/<circuit>.hardblocks(.nets/.pl)")
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
    parser.add_argument("--skip_make", action="store_true",
                        help="跳过 make 编译步骤")
    parser.add_argument("--record_curve", action="store_true",
                        help="记录模拟退火过程中的详细参数曲线")
    parser.add_argument("-a","--algo", type=int, default=0,
                        help="算法模式: 0=原始算法, 1=GMS, 2=... (默认0)")
    parser.add_argument("--tune", type=str, default=None,
                        help="调优配置文件（YAML），对某个参数进行网格搜索。例如: --tune tune_config.yaml")

    # plot and draw
    parser.add_argument("--draw_fp", action="store_true",
                    help="批量实验完成后自动绘制 floorplan 与 B*-tree 图（调用 scripts/draw_fixed_outline.py）")
    parser.add_argument("--draw_curve", action="store_true",
                        help="曲线记录完成后自动绘制模拟退火曲线（调用 scripts/draw_curve.py，需 --record_curve）")
    parser.add_argument("--draw_nets", action="store_true",
                        help="绘制 floorplan 时叠加网表连线（需配合 --draw_fp）")
    parser.add_argument("--max_nets_draw", type=int, default=None,
                        help="绘制网表的最大数量（需配合 --draw_nets）")
    parser.add_argument("--fp_dpi", type=int, default=120,
                        help="floorplan 图片分辨率（默认120）")
    
    return parser.parse_args()

# ---------- 主函数 ----------
def main():
    args = parse_args()
      
    # ===== 新增：调优模式 =====
    if args.tune:
        run_tuning(args)
        return
    # ==========================
    
    script_dir = get_script_dir()
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')    #时间戳
    algo_tag = f"_algo{args.algo}"                              #算法标识
        
    # ===== 第一步：创建统一日志目录结构 =====
    run_dir, log_file = create_run_dirs(args.circuit, args.white_space_ratio,
                                        args.algo, args.num_runs)
    write_config_yaml(run_dir, args)

    # output/log: auto-generate in run_dir by default; or explictly specify a directory
    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
        ensure_dir(output_dir)
    else:
        output_dir = run_dir / "output"       
    
    if args.log_file:
        log_file = Path(args.log_file).resolve()
        ensure_dir(log_file.parent)
            
    curve_dir  = run_dir / "curves"       
    figure_dir = run_dir / "figures"      
    
    print(f"运行目录: {run_dir}")

    # 补全默认路径（相对于脚本目录）
    exec_path, hardblocks, nets, terminals = resolve_common_paths(script_dir, args)

    # 编译
    compile_and_check(exec_path, script_dir, args.skip_make)

    if args.record_curve and args.num_runs > 10:
            args.num_runs = 10
    # ===== 种子 =====
    seeds = load_or_generate_seeds(args.num_runs, args.seed_file,
                                script_dir, algo_tag, timestamp)
    # 种子快照写入 run_dir/seeds/
    seed_snapshot = run_dir / "seeds" / f"seeds_{args.num_runs}{algo_tag}_{timestamp}.txt"
    with open(seed_snapshot, "w") as sf:
        for s in seeds:
            sf.write(f"{s}\n")
            
    # 准备日志文件（写入头部）
    write_log_header(log_file, hardblocks, nets, terminals, args.white_space_ratio, args.num_runs)

    # 用于存储表格数据
    table_data = []   # 每个元素为 (run, seed, width, height, area, wirelength, R, cost)

    print(f"开始批量测试，日志保存到 {log_file}")

    # 批量运行（原逻辑）
    if args.record_curve:
        # 曲线模式：可运行多次，使用特殊处理函数
        print("\n曲线记录模式已开启，将运行多次实验并分别保存曲线数据。\n")

        # 曲线结果目录：run_dir/curves/
        curve_dir.mkdir(parents=True, exist_ok=True)

        for run_idx, seed in enumerate(seeds, start=1):
            floorplan_file = output_dir / f"run{run_idx}_{timestamp}.floorplan"
            # 生成曲线 CSV 文件路径（run_dir/curves/）
            curve_csv_path = curve_dir / f"curve_data_run{run_idx}{algo_tag}.csv"
            print(f"[{run_idx}/{args.num_runs}] 运行中 (曲线记录)...")
            output_text, metrics, retcode = run_with_curve_logging(
                exec_path, hardblocks, nets, terminals,
                floorplan_file, args.white_space_ratio, 
                seed, curve_csv_path, log_file, algo=args.algo, 
                curve=args.record_curve   # 新增
            )
            # 仍然可以收集最终指标到 table_data，以便统计（可选）
            # 提取指标存入表格
            row = _make_metric_row(run_idx, seed, metrics)
            table_data.append(row)
            
            # 终端显示进度
            print(f"[{run_idx}/{args.num_runs}] seed={seed} 完成 (返回码 {retcode})")

            # 附加统计信息到日志文件末尾

            with open(log_file, "a") as lf:
                lf.write(f"\n{'Run: ':<12}{run_idx}")
                lf.write(f"\n{'曲线数据已保存至: ':<12}{curve_csv_path}")
                lf.write(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}\n")
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
            row = _make_metric_row(run_idx, seed, metrics)
            table_data.append(row)

            # 终端显示进度
            print(f"[{run_idx}/{args.num_runs}] seed={seed} 完成 (返回码 {retcode})")

    # ---- 统计输出 ----
    print_statistics_to_console(table_data, args.algo)
    write_statistics_to_log(log_file, table_data, args.algo,
                            mode_desc="曲线模式" if args.record_curve else "批量实验模式")

    # ===== 更新 latest 链接 =====
    update_latest_link(run_dir)

    # ---- 可选：自动绘制 floorplan / B*-tree 图 ----
    if args.draw_fp:
        draw_fp = _load_scripts_module("draw_fixed_outline")
        fp_args = Namespace(
            blocks=int(args.circuit.lstrip('n')),   # 由 circuit 推导块数
            ratio=args.white_space_ratio,
            num_runs=args.num_runs,
            algo=args.algo,
            max_read=None,
            floorplan=None,
            btree=None,
            output=str(figure_dir),                # 图片输出到 run_dir/figures/
            dpi=args.fp_dpi,
            no_labels=False,
            draw_nets=args.draw_nets,
            max_nets_draw=args.max_nets_draw,
            floorplan_dir=str(output_dir),          # 显式传入实验输出目录
        )
        draw_fp.main(fp_args)

    # ---- 可选：自动绘制模拟退火曲线 ----
    if args.draw_curve:
        if not args.record_curve:
            print("提示: --draw_curve 仅在 --record_curve 模式下生效，跳过")
        else:
            draw_curve = _load_scripts_module("draw_curve")
            curve_args = Namespace(
                csv=str(curve_dir),              # run_dir/curves/
                output_dir=str(figure_dir),      # run_dir/figures/
                sample_step=100,
                rejection_rate=None,
                rr_n_top=60,
                n_top=0,
                n_back=0,
                tune=None,
            )
            draw_curve.main(curve_args)

    print(f"\n完整日志保存在: {log_file}")
    print("全部完成。")

if __name__ == "__main__":
    main()