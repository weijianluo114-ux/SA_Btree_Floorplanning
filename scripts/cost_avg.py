#!/usr/bin/env python3
"""
从 tuning/批量实验的 log 文件中提取所有单次运行的 Cost 值，
排除统计汇总行后，计算平均值并输出。

用法:
    python cost_avg.py                              # 自动扫描 ./log/ 下最新的 log 文件
    ↓ <log_file_path>           # 指定 log 文件
    python cost_avg.py -d ./log/tune_algo0_r_2026-06-10_20:17:19  # 扫描目录下所有 param_*/running_results_*.txt
"""

import argparse
import re
import sys
from pathlib import Path
from statistics import mean


def find_latest_log(log_dir: Path) -> Path:
    """在 log_dir 下递归扫描 .txt 文件，返回最新修改的那个"""
    txt_files = list(log_dir.rglob("*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"在 {log_dir} 下未找到任何 .txt 文件")
    latest = max(txt_files, key=lambda p: p.stat().st_mtime)
    return latest


def find_all_param_logs(log_dir: Path):
    """扫描 log_dir 下所有 param_*/running_results_*.txt 文件"""
    files = sorted(log_dir.glob("param_*/running_results_*.txt"))
    return files


def extract_costs_from_file(log_path: Path) -> list[float]:
    """
    从 log 文件中提取所有单次运行的 Cost 值。

    提取策略：
    - 匹配形如 "Cost:       <number>" 的行（带冒号的才是单次运行结果）
    - 忽略统计汇总表格中的 "Cost        <mean>  ..."（不带冒号）
    """
    costs = []
    with open(log_path, "r") as f:
        for line in f:
            m = re.match(r"^\s*Cost:\s+([0-9.]+)", line)
            if m:
                val = float(m.group(1))
                if val < 1.0:
                    costs.append(val)
    return costs


def main():
    parser = argparse.ArgumentParser(description="从 log 文件中提取单次 Cost 并计算平均值")
    parser.add_argument("-f", "--file", type=str, default=None,
                        help="log 文件路径（若未指定则自动扫描 ./log/）")
    parser.add_argument("-d", "--dir", type=str, default=None,
                        help="扫描指定目录下所有 param_*/running_results_*.txt")
    parser.add_argument("--all", action="store_true",
                        help="配合 -d 使用：输出每个参数子目录的平均 Cost 汇总表")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    log_dir = script_dir / "../log"

    # ---------- 确定要处理的文件 ----------
    files_to_process = []

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"错误: 文件不存在: {file_path}", file=sys.stderr)
            sys.exit(1)
        files_to_process = [file_path]

    elif args.dir:
        target_dir = Path(args.dir) if Path(args.dir).is_absolute() else (script_dir / ".." / args.dir)
        if not target_dir.exists():
            print(f"错误: 目录不存在: {target_dir}", file=sys.stderr)
            sys.exit(1)
        files_to_process = find_all_param_logs(target_dir)
        if not files_to_process:
            print(f"错误: 在 {target_dir} 下未找到 param_*/running_results_*.txt", file=sys.stderr)
            sys.exit(1)

    else:
        log_dir_resolved = log_dir.resolve()
        if not log_dir_resolved.exists():
            print(f"错误: log 目录不存在: {log_dir_resolved}", file=sys.stderr)
            sys.exit(1)
        latest_file = find_latest_log(log_dir_resolved)
        print(f"自动选择最新 log 文件: {latest_file}")
        files_to_process = [latest_file]

    # ---------- 处理文件 ----------
    if args.all and len(files_to_process) > 1:
        # 汇总模式：输出每个参数子目录的平均 Cost
        print(f"{'参数名':<20} {'运行次数':<10} {'平均Cost':<12}")
        print("-" * 45)
        for fpath in files_to_process:
            costs = extract_costs_from_file(fpath)
            if not costs:
                continue
            param_dir = fpath.parent.name
            param_name = param_dir.replace("param_", "")
            avg_cost = mean(costs)
            print(f"{param_name:<20} {len(costs):<10} {avg_cost:<12.4f}")
    else:
        for fpath in files_to_process:
            costs = extract_costs_from_file(fpath)
            if not costs:
                print(f"警告: 从 {fpath} 中未提取到有效 Cost 值", file=sys.stderr)
                continue

            avg_cost = mean(costs)
            print(f"文件: {fpath}")
            print(f"有效运行次数: {len(costs)}")
            print(f"Cost 平均值:  {avg_cost:.6f}")
            print(f"最小 Cost:    {min(costs):.6f}")
            print(f"最大 Cost:    {max(costs):.6f}")
            if len(costs) > 1:
                var = sum((c - avg_cost) ** 2 for c in costs) / len(costs)
                print(f"标准差:      {var ** 0.5:.6f}")
            print()


if __name__ == "__main__":
    main()