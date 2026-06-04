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
from pathlib import Path
from datetime import datetime
import statistics
from typing import Dict, List, Optional, Tuple
import re


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

def parse_output(output_text: str) -> Dict[str, Optional[float]]:
    """
    从程序输出中提取指标，包括耗时和可行解状态。
    返回字典：
        - 数值指标：Width, Height, Area, Wirelength, R, Cost,
                     BuildTree_T_us, SA_T_s
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
        "BuildTree_T_us": r"\[BuildInitBtree\] 耗时:\s+(\d+)\s*us",
        "SA_T_s": r"\[SimulatedAnnealing\] 耗时:\s+([0-9.]+)\s*s",
    }
    result = {}
    for key, pat in patterns.items():
        match = re.search(pat, output_text)
        if match:
            val = match.group(1)
            if key in ["BuildTree_T_us", "SA_T_s"]:
                result[key] = float(val)
            elif '.' in val:
                result[key] = float(val)
            else:
                result[key] = int(val)
        else:
            result[key] = None

    # 检测可行解：出现 "Not Found feasible solution" 则标记为 0，否则为 1
    if re.search(r"Not Found feasible solution", output_text):
        result["Feasible"] = 0
    else:
        result["Feasible"] = 1

    return result

def run_single(exec_path: Path, hardblocks: str, nets: str, terminals: str,
               floorplan_file: Path, ratio: float, seed: int) -> Tuple[str, Dict[str, Optional[float]], int]:
    """
    运行一次实验，返回 (原始输出, 提取的指标字典, 返回码)
    """
    cmd = [str(exec_path), hardblocks, nets, terminals, str(floorplan_file), str(ratio), str(seed)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = proc.stdout + proc.stderr
        metrics = parse_output(output)
        return output, metrics, proc.returncode
    except Exception as e:
        error_output = f"运行失败: {e}\n"
        return error_output, {}, -1

# ---------- 主函数 ----------
def main():
    args = parse_args()
    script_dir = get_script_dir()

    # 补全默认路径（相对于脚本目录）
    exec_path = (script_dir / args.executable).resolve()
    hardblocks = str((script_dir / args.hardblocks).resolve())
    nets = str((script_dir / args.nets).resolve())
    terminals = str((script_dir / args.terminals).resolve())

    # 输出目录
    if args.output_dir is None:
        # 从 hardblocks 文件名中提取模块数量（如 n100.hardblocks -> 100）
        match = re.search(r'(\d+)', args.hardblocks)
        if match:
            num_blocks = match.group(1)
        else:
            num_blocks = "unknown"
        # 将浮点数 white_space_ratio 中的小数点替换为下划线，避免路径问题
        ratio_str = str(args.white_space_ratio).replace('.', '_')
        output_dir = script_dir / f"./output/test_{num_blocks}blocks_ratio_{ratio_str}_total_{args.num_runs}"
    else:
        output_dir = Path(args.output_dir)
    output_dir = output_dir.resolve()
    ensure_dir(output_dir)

    # 日志文件（原始输出）
    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    if args.log_file is None:
        log_file = script_dir / f"./log/running_results_{timestamp}.txt"
    else:
        log_file = Path(args.log_file)
    log_file = log_file.resolve()
    ensure_dir(log_file.parent)

    # 种子文件
    if args.seed_file is None:
        seed_file = script_dir / f"./seeds/seeds_{args.num_runs}_{timestamp}.txt"
    else:
        seed_file = Path(args.seed_file)
    seed_file = seed_file.resolve()
    ensure_dir(seed_file.parent)

    # 结果 CSV 文件
    if args.results_csv is None:
        results_csv = script_dir / f"./results/n_runs_result/results_{args.num_runs}_{timestamp}.csv"
    else:
        results_csv = Path(args.results_csv)
    results_csv = results_csv.resolve()
    ensure_dir(results_csv.parent)

    # 编译
    if not args.skip_make:
        cpp_src_dir = script_dir / "cpp_src"
        if not cpp_src_dir.exists():
            print(f"错误: cpp_src 目录不存在: {cpp_src_dir}", file=sys.stderr)
            sys.exit(1)
        run_make(cpp_src_dir)

    # 检查可执行文件
    if not exec_path.exists():
        print(f"错误: 可执行文件不存在: {exec_path}", file=sys.stderr)
        sys.exit(1)

    # 生成种子
    print(f"生成 {args.num_runs} 个随机种子...")
    seeds = generate_seeds(args.num_runs)
    # 保存种子文件
    with open(seed_file, "w") as sf:
        for s in seeds:
            sf.write(f"{s}\n")
    print(f"种子已保存到 {seed_file}")

    # 准备日志文件（写入头部）
    with open(log_file, "w") as lf:
        lf.write("=" * 46 + "\n")
        lf.write("Batch floorplanning experiment\n")
        lf.write(f"Hardblocks: {hardblocks}\n")
        lf.write(f"Nets:       {nets}\n")
        lf.write(f"Terminals:  {terminals}\n")
        lf.write(f"Ratio:      {args.white_space_ratio}\n")
        lf.write(f"Runs:       {args.num_runs}\n")
        lf.write(f"Start time: {datetime.now().strftime('%c')}\n")
        lf.write("=" * 46 + "\n\n")

    # 用于存储表格数据
    table_data = []   # 每个元素为 (run, seed, width, height, area, wirelength, R, cost)

    print(f"开始批量测试，日志保存到 {log_file}")
    print(f"结果表格将保存到 {results_csv}")

    # 批量运行
    for run_idx, seed in enumerate(seeds, start=1):
        floorplan_file = output_dir / f"run{run_idx}.floorplan"
        print(f"[{run_idx}/{args.num_runs}] seed={seed} 运行中...")

        output_text, metrics, retcode = run_single(
            exec_path, hardblocks, nets, terminals,
            floorplan_file, args.white_space_ratio, seed
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
            metrics.get("BuildTree_T_us"),
            metrics.get("SA_T_s"),
            metrics.get("Feasible"),   # 添加可行解标记
        ]
        table_data.append(row)

        # 终端显示进度
        print(f"[{run_idx}/{args.num_runs}] seed={seed} 完成 (返回码 {retcode})")

    # 写入 CSV 表格
    with open(results_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "run", "seed", "Width", "Height", "Area", "Wirelength", "R", "Cost",
            "BuildTree_T_us", "SA_T_s", "Feasible"
        ])
        for row in table_data:
            writer.writerow(row)

    print(f"\n结果表格已保存到 {results_csv}")

    # 统计分析（忽略 None 值）
    stats = {}
    # 在原有 stats 构建循环中加入 Feasible
    for col_idx, col_name in enumerate([
        "Width", "Height", "Area", "Wirelength", "R", "Cost",
        "BuildTree_T_us", "SA_T_s", "Feasible"
    ], start=2):
        values = [row[col_idx] for row in table_data if row[col_idx] is not None]
        if values:
            mean_val = statistics.mean(values)
            variance_val = statistics.variance(values) if len(values) > 1 else 0.0
            stats[col_name] = (mean_val, variance_val)
        else:
            stats[col_name] = (None, None)


    # 输出统计信息到控制台和日志文件
    print("\n========== 统计结果 ==========")
    print(f"{'指标':<12} {'平均值':<15} {'方差':<15}")
    print("-" * 42)
    for name, (mean_val, var_val) in stats.items():
        if mean_val is not None:
            print(f"{name:<12} {mean_val:<15.4f} {var_val:<15.4f}")
        else:
            print(f"{name:<12} {'无有效数据':<15} {'无有效数据':<15}")

    #寻找可行解
    feasible_values = [row[-1] for row in table_data if row[-1] is not None]
    if feasible_values:
            found_count = sum(feasible_values)  # 因为 Feasible=1 表示 found
            not_found_count = len(feasible_values) - found_count
    else:
        found_count = None   
        not_found_count = None     

    # 附加统计信息到日志文件末尾
    with open(log_file, "a") as lf:
        lf.write("\n" + "=" * 46 + "\n")
        lf.write("统计汇总（基于成功提取的数据）\n")
        lf.write(f"{'指标':<12} {'平均值':<15} {'方差':<15}\n")
        lf.write("-" * 42 + "\n")
        for name, (mean_val, var_val) in stats.items():
            if mean_val is not None:
                lf.write(f"{name:<12} {mean_val:<15.4f} {var_val:<15.4f}\n")
            else:
                lf.write(f"{name:<12} {'无有效数据':<15} {'无有效数据':<15}\n")
            # 统计可行解数量
        lf.write(f"可行解统计: found = {found_count}, not found = {not_found_count}\n")
        lf.write(f"\n结束时间: {datetime.now().strftime('%c')}\n")
        lf.write("=" * 46 + "\n")

    print(f"\n完整日志保存在: {log_file}")
    print(f"种子文件保存在: {seed_file}")
    print("全部完成。")

if __name__ == "__main__":
    main()