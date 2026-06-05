#!/usr/bin/env python3
"""
绘制模拟退火曲线图
用法：
    python plot_curve.py --csv /path/to/curve.csv
或自动读取最新CSV：
    python plot_curve.py
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from pathlib import Path
import re
from datetime import datetime
import numpy as np

DPI = 300   #全局图像DPI

# 设置中文字体（避免中文标签乱码，可选）
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']  # 或 'WenQuanYi Zen Hei'
plt.rcParams['axes.unicode_minus'] = False

def find_latest_csv(results_dir: Path) -> Path:
    """扫描 curve_results 目录，找到最新生成的 CSV 文件（基于文件名中的时间戳）"""
    csv_files = list(results_dir.glob("curve_data_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"在 {results_dir} 中未找到任何 curve_data_*.csv 文件")
    
    def extract_timestamp(path: Path) -> datetime:
        # 兼容: curve_data_2026-06-04_12:48:28.csv
        # 兼容: curve_data_run6_2026-06-04_20:42:11.csv
        name = path.stem  # e.g. curve_data_run6_2026-06-04_20:42:11
        m = re.search(r"\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2}", name)
        if m:
            return datetime.strptime(m.group(0), "%Y-%m-%d_%H:%M:%S")
        # 回退到文件修改时间
        return datetime.fromtimestamp(path.stat().st_mtime)
    
    latest = max(csv_files, key=extract_timestamp)
    return latest

def plot_single_metric(df, metric, x_col, suffix, output_dir, logy=False):
    """绘制单个指标随 Total_Moves 的变化图"""
    plt.figure(figsize=(10, 6))
    plt.plot(df[x_col], df[metric], linewidth=1.5)
    plt.xlabel('Total Moves')
    plt.ylabel(metric)
    plt.title(f'{metric} vs Total Moves')
    if logy:
        plt.yscale('log')
    plt.grid(True, alpha=0.3)
    # 命名：metric_suffix.png
    filename = f"{metric}_{suffix}.png"
    filepath = output_dir / filename
    plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"已保存: {filepath}")

def plot_all_metrics_subplots(df, x_col, suffix, output_dir):
    """绘制6个指标在同一个图中（2行3列子图），每个子图使用对数Y轴"""
    metrics = ['width', 'height', 'area', 'wirelength', 'R', 'cost']
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    for ax, metric in zip(axes, metrics):
        ax.plot(df[x_col], df[metric], linewidth=1.5)
        ax.set_xlabel('Total Moves')
        ax.set_ylabel(metric)
        ax.set_title(f'{metric} (log scale)')
        ax.set_yscale('log')
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    filename = f"all_metrics_logy_{suffix}.png"
    filepath = output_dir / filename
    plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"已保存: {filepath}")

def plot_temperature_behaviors(df, suffix, output_dir, n_front=5, n_back=5):
    """
    绘制前 n_front 个非零温度和最后 n_back 个温度下的 T_uphill, T_reject 随 T_Moves 的变化。
    每个温度单独一张图，使用双Y轴（左：T_uphill，右：T_reject）。
    """
    # 获取唯一的温度值，排除0，并按升序排序
    temps = sorted(df[df['T'] != 0]['T'].unique())
    if len(temps) == 0:
        print("警告：没有非零温度数据，跳过温度行为图。")
        return

    # 选择前 n_front 和末 n_back，并用 set 去重（避免重叠导致覆盖）
    selected_temps = sorted(set(temps[:n_front]) | set(temps[-n_back:]))

    for temp in selected_temps:
        subset = df[df['T'] == temp].copy()
        if subset.empty:
            print(f"警告：温度 T={temp} 无数据，跳过")
            continue

        # 绘图部分（双Y轴，动态范围）
        fig, ax1 = plt.subplots(figsize=(12, 6))

        color_uphill = 'tab:blue'
        ax1.plot(subset['T_Moves'], subset['T_uphill'],
                 color=color_uphill, label='T_uphill', linewidth=1.5)
        ax1.set_xlabel('T_Moves (cumulative moves within this temperature)')
        ax1.set_ylabel('T_uphill', color=color_uphill)
        ax1.tick_params(axis='y', labelcolor=color_uphill)
        max_uphill = subset['T_uphill'].max()
        ax1.set_ylim(0, max_uphill * 1.1 if max_uphill > 0 else 1)

        ax2 = ax1.twinx()
        color_reject = 'tab:red'
        ax2.plot(subset['T_Moves'], subset['T_reject'],
                 color=color_reject, label='T_reject', linewidth=1.5)
        ax2.set_ylabel('T_reject', color=color_reject)
        ax2.tick_params(axis='y', labelcolor=color_reject)
        max_reject = subset['T_reject'].max()
        ax2.set_ylim(0, max_reject * 1.1 if max_reject > 0 else 1)

        plt.title(f'Temperature T = {temp:.6f} : Uphill and Reject Moves')
        # 合并图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='best')
        ax1.grid(True, alpha=0.3)

        temp_label = str(temp).replace('.', '_')
        filename = f"T_{temp_label}_uphill_reject_{suffix}.png"
        filepath = output_dir / filename
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
        plt.close()
        print(f"已保存: {filepath}")

def main():
    parser = argparse.ArgumentParser(description="绘制模拟退火曲线")
    parser.add_argument("--csv", type=str, default=None,
                        help="CSV 文件路径（若未指定，则自动使用 ./results/curve_results 下的最新文件）")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="图片输出目录（默认 ./results/curve_figures）")
    args = parser.parse_args()

    # 确定脚本所在目录
    script_dir = Path(__file__).resolve().parent
    results_curve_dir = script_dir / "../results/curve_results"

    # 定位 CSV 文件
    if args.csv:
        csv_path = Path(args.csv)
        if not csv_path.exists():
            raise FileNotFoundError(f"指定的 CSV 文件不存在: {csv_path}")
    else:
        csv_path = find_latest_csv(results_curve_dir)
    print(f"读取 CSV: {csv_path}")

    #创建输出文件夹
    if args.output_dir is None:
        base_dir = script_dir / "../results/curve_figures"
        # 使用 CSV 文件名（不含扩展名）作为子文件夹名
        subfolder_name = csv_path.stem   # 例如 "curve_data_2026-06-04_12:48:28"
        output_dir = base_dir / subfolder_name
    else:
        output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 读取数据
    df = pd.read_csv(csv_path)
    # 确保列存在
    required_cols = ['width', 'height', 'area', 'wirelength', 'R', 'cost', 'Total_Moves', 'T_Moves', 'T_uphill', 'T_reject', 'T']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"CSV 文件中缺少列: {col}")

    # 生成后缀（基于 CSV 文件名去掉扩展名，保留 curve_data_时间部分）
    suffix = csv_path.stem  # 直接使用完整文件名作为后缀

    # 1. 单独图（线性Y轴）
    print("绘制单个指标线性图...")
    metrics = ['width', 'height', 'area', 'wirelength', 'R', 'cost']
    for m in metrics:
        plot_single_metric(df, m, 'Total_Moves', suffix, output_dir, logy=False)

    # 2. 总图（6个子图，对数Y轴）
    print("绘制总图（对数Y轴子图）...")
    plot_all_metrics_subplots(df, 'Total_Moves', suffix, output_dir)

    # 3. 温度行为图（前5和后5个非零温度）
    print("绘制温度行为图...")
    plot_temperature_behaviors(df, suffix, output_dir, n_front=5, n_back=5)

    print("全部绘图完成！")

if __name__ == "__main__":
    main()