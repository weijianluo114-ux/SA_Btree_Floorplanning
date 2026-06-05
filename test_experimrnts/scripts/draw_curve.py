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
from pathlib import Path
import re
from datetime import datetime

DPI = 300   #全局图像DPI

# 设置中文字体（避免中文标签乱码，可选）
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']  # 或 'WenQuanYi Zen Hei'
plt.rcParams['axes.unicode_minus'] = False

# ---------- 辅助函数 ----------
def find_latest_csv_dir(results_dir: Path) -> Path:
    """扫描 curve_results 目录，找到最新生成的子文件夹（基于文件名中的时间戳）"""
    subdirs = [d for d in results_dir.iterdir() if d.is_dir() and d.name.startswith("curve_data_")]
    if not subdirs:
        raise FileNotFoundError(f"在 {results_dir} 中未找到任何 curve_data_* 子文件夹")
    def extract_timestamp(path: Path) -> datetime:
        # 文件夹名格式: curve_data_2026-06-04_12:48:28
        name = path.name
        parts = name.split('_')
        if len(parts) >= 3:
            date_str = '_'.join(parts[2:])  # 2026-06-04_12:48:28
            return datetime.strptime(date_str, "%Y-%m-%d_%H:%M:%S")
        else:
            return datetime.fromtimestamp(path.stat().st_mtime)
    latest = max(subdirs, key=extract_timestamp)
    return latest

def process_single_csv(csv_path: Path, output_dir: Path, suffix: str):
    """处理单个CSV文件，绘制所有曲线，输出到 output_dir"""
    output_dir.mkdir(parents=True, exist_ok=True)
    if suffix is None:
        suffix = csv_path.stem   # 如 "curve_data_run1"
    print(f"处理 CSV: {csv_path}，输出目录: {output_dir}")

    df = pd.read_csv(csv_path)
    required_cols = ['width', 'height', 'area', 'wirelength', 'R', 'cost', 'Total_Moves', 'T_Moves', 'T_uphill', 'T_reject', 'T']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"CSV 文件中缺少列: {col}")

    # 1. 单独线性图
    print("绘制单个指标线性图...")
    metrics = ['width', 'height', 'area', 'wirelength', 'R', 'cost']
    for m in metrics:
        plot_single_metric(df, m, 'Total_Moves', suffix, output_dir, logy=False)

    # 2. 总图（对数Y轴）
    print("绘制总图（对数Y轴子图）...")
    plot_all_metrics_subplots(df, 'Total_Moves', suffix, output_dir)

    # 3. 温度行为图
    print("绘制温度行为图...")
    plot_temperature_behaviors(df, suffix, output_dir, n_front=50, n_back=70)

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

# ---------- 主函数 ----------
def main():
    parser = argparse.ArgumentParser(description="批量绘制模拟退火曲线（支持多个run文件）")
    parser.add_argument("--csv", type=str, default=None,
                        help="CSV 文件路径 或 包含多个CSV的目录。若为目录，则处理其中所有 curve_data_run*.csv 文件。"
                             "若未指定，则自动使用 ./results/curve_results 下的最新时间戳文件夹。")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="图片输出根目录（默认 ./results/curve_figures）。每个run的图片会放在该目录下的子文件夹中。")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    results_curve_root = script_dir / "../results/curve_results"

    # ----- 确定要处理的CSV文件列表 -----
    csv_files = []
    run_ids = []   # 用于命名子文件夹
    if args.csv:
        path = Path(args.csv)
        if path.is_file():
            csv_files = [path]
            run_ids = [None]   # 后续会尝试从文件名提取
        elif path.is_dir():
            files = sorted(path.glob("curve_data_run*.csv"))
            if not files:
                raise FileNotFoundError(f"目录 {path} 中没有找到 curve_data_run*.csv 文件")
            csv_files = files
            # 提取run编号
            for f in files:
                match = re.search(r'run(\d+)', f.stem)
                run_ids.append(int(match.group(1)) if match else None)
        else:
            raise FileNotFoundError(f"路径不存在: {path}")
    else:
        # 自动查找最新时间戳文件夹
        latest_dir = find_latest_csv_dir(results_curve_root)
        print(f"自动选择最新文件夹: {latest_dir}")
        files = sorted(latest_dir.glob("curve_data_run*.csv"))
        if not files:
            raise FileNotFoundError(f"在 {latest_dir} 中没有找到 curve_data_run*.csv 文件")
        csv_files = files
        for f in files:
            match = re.search(r'run(\d+)', f.stem)
            run_ids.append(int(match.group(1)) if match else None)

    # ----- 确定输出根目录 -----
    if args.output_dir:
        base_output_dir = Path(args.output_dir)
    else:
        # 如果用户没有指定输出根目录，则默认为 ./results/curve_figures/
        # 并且如果当前处理的是自动找到的时间戳文件夹，则在该目录下创建同名子文件夹
        if 'latest_dir' in locals():
            base_output_dir = script_dir / "../results/curve_figures" / latest_dir.name
        else:
            # 用户指定了单个文件或目录，但没有指定 --output_dir，则直接在 curve_figures 下以CSV文件（或目录）命名
            if len(csv_files) == 1 and csv_files[0].parent != results_curve_root:
                # 单个文件，且不在标准位置：使用该文件的父目录名？为简单，直接使用 curve_figures 根目录
                base_output_dir = script_dir / "../results/curve_figures"
            else:
                # 多个文件，或文件位于某个子目录（如最新时间戳文件夹），则使用该子目录名
                parent_dir = csv_files[0].parent
                base_output_dir = script_dir / "../results/curve_figures" / parent_dir.name
    base_output_dir.mkdir(parents=True, exist_ok=True)

    # ----- 逐个处理CSV文件 -----
    for csv_path, run_id in zip(csv_files, run_ids):
        # 决定每个run的输出子文件夹
        if run_id is not None:
            output_subdir = base_output_dir / f"run{run_id}"
        else:
            # 对于没有run编号的文件，使用文件名（不含扩展名）
            output_subdir = base_output_dir / csv_path.stem
        # 调用处理函数
        process_single_csv(csv_path, output_subdir, suffix=csv_path.stem)

    print("全部绘图完成！")

if __name__ == "__main__":
    main()