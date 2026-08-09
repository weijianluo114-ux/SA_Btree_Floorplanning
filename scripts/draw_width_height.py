#!/usr/bin/env python3
"""
读取 n_runs_result 目录下的 CSV 结果文件，绘制 Width 和 Height 的折线图。
用法：
    python plot_width_height.py --csv ../results/n_runs_result/results_50_algo0_2026-06-07_17:04:29.csv
或自动读取最新 CSV：
    python plot_width_height.py
"""

import argparse
import re
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

DPI = 400

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def find_latest_csv(results_dir: Path) -> Path:
    """在 n_runs_result 目录下找到最新的 CSV 文件"""
    csv_files = list(results_dir.glob("results_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"在 {results_dir} 中未找到 results_*.csv 文件")

    def extract_timestamp(path: Path) -> datetime:
        name = path.stem
        # 文件名格式: results_50_algo0_2026-06-07_17:04:29
        m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2})", name)
        if m:
            return datetime.strptime(m.group(1), "%Y-%m-%d_%H:%M:%S")
        return datetime.fromtimestamp(path.stat().st_mtime)

    latest = max(csv_files, key=extract_timestamp)
    return latest


def plot_width_height(csv_path: Path, output_dir: Path):
    """绘制 Width 和 Height 的折线图"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 读取 CSV
    df = pd.read_csv(csv_path)
    required_cols = ['run', 'Width', 'Height']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"CSV 文件中缺少列: {col}")

    runs = df['run']
    width_vals = df['Width']
    height_vals = df['Height']

    # 计算纵轴范围
    # all_vals = pd.concat([width_vals, height_vals])
    # y_max = all_vals.max() * 1.1

    # 绘图
    plt.figure(figsize=(12, 6))

    plt.plot(runs, width_vals, color='tab:red', marker='o',
             linestyle='-', linewidth=1.5, markersize=4, label='Width')
    plt.plot(runs, height_vals, color='tab:blue', marker='s',
             linestyle='-', linewidth=1.5, markersize=4, label='Height')

    # y=444 黑色虚线
    plt.axhline(y=444, color='black', linestyle='--', linewidth=1.0, label='Target y=444')

    plt.xlabel('Runs', fontsize=16)
    plt.ylabel('Width/Height Value', fontsize=16)
    plt.ylim(410, 480)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.legend(fontsize=14)
    # plt.grid(True, alpha=0.3)

    plt.tight_layout()

    # 输出文件名：包含算法和种子数信息
    stem = csv_path.stem  # 如 results_50_algo0_2026-06-07_17:04:29
    filename = f"width_height_{stem}.png"
    filepath = output_dir / filename
    plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"已保存: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="绘制 Width/Height 折线图")
    parser.add_argument("--csv", type=str, default=None,
                        help="CSV 文件路径（如 ../results/n_runs_result/results_50_algo0_xxx.csv）。"
                             "若未指定，则自动使用 n_runs_result 下最新的 CSV。")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    results_dir = script_dir / "../results/n_runs_result"

    # 确定 CSV 文件
    if args.csv:
        csv_path = Path(args.csv)
        if not csv_path.is_file():
            raise FileNotFoundError(f"文件不存在: {csv_path}")
    else:
        csv_path = find_latest_csv(results_dir)
        print(f"自动选择最新 CSV: {csv_path}")

    # 输出目录：./results/curve_figures/<csv_stem>/
    csv_stem = csv_path.stem
    output_dir = script_dir / "../results/curve_figures" / csv_stem
    output_dir.mkdir(parents=True, exist_ok=True)

    plot_width_height(csv_path, output_dir)
    print("绘制完成！")


if __name__ == "__main__":
    main()