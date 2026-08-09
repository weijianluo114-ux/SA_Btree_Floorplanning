#!/usr/bin/env python3
"""
绘制模拟退火曲线图
用法：
    python plot_curve.py --csv /path/to/curve.csv
或自动读取最新CSV：
    python plot_curve.py
"""

import argparse
from matplotlib.colors import Normalize
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import re
from datetime import datetime
import numpy as np
from matplotlib.collections import LineCollection


DPI = 400   #全局图像DPI

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
        # 兼容旧格式: curve_data_2026-06-04_12:48:28
        # 兼容新格式: curve_data_algo0_2026-06-06_20:48:33_algo0
        name = path.name
        m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2})", name)
        if m:
            return datetime.strptime(m.group(1), "%Y-%m-%d_%H:%M:%S")
        return datetime.fromtimestamp(path.stat().st_mtime)
    latest = max(subdirs, key=extract_timestamp)
    return latest

def find_latest_csv(results_dir: Path) -> Path:
    """扫描 curve_results 目录，找到最新生成的 CSV 文件（基于文件名中的时间戳）"""
    csv_files = list(results_dir.glob("curve_data_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"在 {results_dir} 中未找到任何 curve_data_*.csv 文件")
    
    def extract_timestamp(path: Path) -> datetime:
        # 兼容: curve_data_2026-06-04_12:48:28.csv
        # 兼容: curve_data_run6_2026-06-04_20:42:11.csv
        name = path.stem
        m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2})", name)
        if m:
            return datetime.strptime(m.group(1), "%Y-%m-%d_%H:%M:%S")
        return datetime.fromtimestamp(path.stat().st_mtime)
    
    latest = max(csv_files, key=extract_timestamp)
    return latest

def find_latest_tune_dir(results_dir: Path) -> Path:
    """扫描 curve_results 目录，找到最新的 tune_* 子文件夹"""
    subdirs = [d for d in results_dir.iterdir() if d.is_dir() and d.name.startswith("tune_")]
    if not subdirs:
        raise FileNotFoundError(f"在 {results_dir} 中未找到任何 tune_* 子文件夹")
    def extract_timestamp(path: Path) -> datetime:
        name = path.name
        m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2})", name)
        if m:
            return datetime.strptime(m.group(1), "%Y-%m-%d_%H:%M:%S")
        return datetime.fromtimestamp(path.stat().st_mtime)
    latest = max(subdirs, key=extract_timestamp)
    return latest

def process_single_csv(csv_path, output_dir, suffix, sample_step=100, algo=0,
                       n_top=0, n_back=0):
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

    metrics = ['width', 'height', 'area', 'wirelength', 'R', 'cost']
    def _plot_all_for_df(df, suffix, output_dir, sample_step, algo):
        """绘制一个 DataFrame 的所有标准曲线（单指标图 + 总图）"""
        # ... 从原 process_single_csv 中提取的代码 ...
        for m in metrics:
            plot_single_metric(df, m, 'Total_Moves', suffix, output_dir,
                            logy=False, sample_step=sample_step, algo=algo)
        plot_single_metric(df, 'T', 'Total_Moves', suffix, output_dir,
                        logy=True, sample_step=sample_step, algo=algo)
        plot_all_metrics_subplots(df, 'Total_Moves', suffix, output_dir, algo=algo)


    # 1. 单独线性图
    print("绘制单个指标线性图...")
    _plot_all_for_df(df, suffix, output_dir, sample_step, algo)

    # 3. 温度行为图
    # print("绘制温度行为图...")
    # plot_temperature_behaviors(df, suffix, output_dir, n_front=2, n_back=2, algo=algo)
    
    # 2. 前 N 行
    if n_top > 0:
        n_top_actual = min(n_top, len(df))
        print(f"绘制前 {n_top_actual} 个数据点曲线...")
        df_first = df.head(n_top_actual)
        _plot_all_for_df(df_first, f"{suffix}_first{n_top_actual}",
                        output_dir, sample_step=1, algo=algo)  
        # sample_step=1 避免过采样导致子集点太少

    # 3. 后 N 行
    if n_back > 0:
        n_back_actual = min(n_back, len(df))
        print(f"绘制后 {n_back_actual} 个数据点曲线...")
        df_last = df.tail(n_back_actual)
        _plot_all_for_df(df_last, f"{suffix}_last{n_back_actual}",
                        output_dir, sample_step=1, algo=algo)

def plot_single_metric(df, metric, x_col, suffix, output_dir, logy=False, sample_step=100, algo=0):
    """
    绘制单个指标随 Total_Moves 的变化图（曲线图），线段颜色代表温度（对数映射）。
    过滤温度为零的点，颜色映射范围基于非零温度的最大最小值。
    """
    # 采样
    df_sampled = df.iloc[::sample_step, :].copy()
    # 过滤温度等于0的行
    df_sampled = df_sampled[df_sampled['T'] != 0].copy()
    if df_sampled.empty:
        print(f"警告: {metric} 无有效非零温度数据，跳过绘图")
        return

    # 准备数据
    x = df_sampled[x_col].values
    y = df_sampled[metric].values
    T = df_sampled['T'].values

    # 对温度取对数（用于颜色映射），避免零值（已过滤）
    logT = np.log10(T)
    vmin_log, vmax_log = logT.min(), logT.max()

    # 构造线段集合：每个线段连接 (x[i], y[i]) 到 (x[i+1], y[i+1])
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    # 每段线段的颜色使用该线段起点温度的对数值（或平均）
    segment_logT = logT[:-1]  # 用起点温度

    # 创建 LineCollection
    lc = LineCollection(segments, cmap='jet', norm=Normalize(vmin_log, vmax_log))
    lc.set_array(segment_logT)
    lc.set_linewidth(1.5)

    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    ax.add_collection(lc)

    # 设置坐标轴范围
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(y.min(), y.max())
    if logy:
        ax.set_yscale('log')

    ax.set_xlabel('Total Moves')
    ax.set_ylabel(metric)
    # ax.set_title(f'{metric} vs Total Moves (line color = log10(T), sampled every {sample_step})(alog{algo})')
    # ax.grid(True, alpha=0.3)

    # 添加 colorbar，显示真实温度值
    cbar = plt.colorbar(lc, ax=ax, ticks=np.linspace(vmin_log, vmax_log, 5))
    tick_labels = [f'{10**tick:.1e}' for tick in cbar.get_ticks()]
    cbar.set_ticklabels(tick_labels)
    cbar.set_label('Temperature T (log scale)')

    filename = f"{metric}_heatmap_{suffix}.png"
    filepath = output_dir / filename
    plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"已保存: {filepath}")

def plot_all_metrics_subplots(df, x_col, suffix, output_dir, sample_step=100, algo=0):
    """
    绘制6个指标子图（曲线图），线段颜色代表温度（对数映射），过滤零温度。
    """
    df_sampled = df.iloc[::sample_step, :].copy()
    df_sampled = df_sampled[df_sampled['T'] != 0].copy()
    if df_sampled.empty:
        print("警告: 无有效非零温度数据，跳过总图")
        return

    x = df_sampled[x_col].values
    logT = np.log10(df_sampled['T'].values)
    vmin_log, vmax_log = logT.min(), logT.max()

    metrics = ['width', 'height', 'area', 'wirelength', 'R', 'cost']
    fig, axes = plt.subplots(2, 3, figsize=(24, 16))
    axes = axes.flatten()

    # 共享颜色条时，需要收集所有线段对象
    line_collections = []

    for ax, metric in zip(axes, metrics):
        y = df_sampled[metric].values
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        segment_logT = logT[:-1]

        lc = LineCollection(segments, cmap='jet', norm=Normalize(vmin_log, vmax_log))
        lc.set_array(segment_logT)
        lc.set_linewidth(1.5)
        ax.add_collection(lc)

        ax.set_xlim(x.min(), x.max())
        ax.set_ylim(y.min(), y.max())
        ax.set_yscale('log')
        ax.set_xlabel('Total Moves')
        ax.set_ylabel(metric)
        ax.set_title(f'{metric} (log scale, color=log10(T))')
        # ax.grid(True, alpha=0.3)

        line_collections.append(lc)

    # 调整子图布局，为右侧 colorbar 预留空间
    plt.subplots_adjust(right=0.88)  # 右侧留出12%空白

    # 创建专用于 colorbar 的轴（位于右侧，垂直居中）
    cbar_ax = fig.add_axes((0.90, 0.15, 0.02, 0.7))  # [left, bottom, width, height]
    cbar = fig.colorbar(line_collections[-1], cax=cbar_ax, ticks=np.linspace(vmin_log, vmax_log, 5))
    tick_labels = [f'{10**tick:.1e}' for tick in cbar.get_ticks()]
    cbar.set_ticklabels(tick_labels)
    cbar.set_label(f'Temperature T (log scale)(algo{algo})')

    # 不要调用 plt.tight_layout()，否则会覆盖手动调整
    # plt.tight_layout()   # 注释或删除

    # plt.tight_layout()
    filename = f"all_metrics_heatmap_{suffix}.png"
    filepath = output_dir / filename
    plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f"已保存: {filepath}")

def plot_temperature_behaviors(df, suffix, output_dir, n_front=5, n_back=5, algo=0):
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

        plt.title(f'(algo{algo})Temperature T = {temp:.6f} : Uphill and Reject Moves')
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

def plot_rejection_rates(csv_files, output_dir, algo=0, n_top=60):
    """
    绘制多个CSV文件的前 n_top 个最高温度的拒绝率散点图（同一张图）。
    拒绝率 = T_reject / T_Moves（取每个温度最后一行的累计值）。
    不同CSV文件用不同颜色区分。
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 使用 tab10 colormap 区分不同文件
    import matplotlib.cm as cm
    colors = cm.tab10(np.linspace(0, 1, len(csv_files)))

    plt.figure(figsize=(14, 8))

    for idx, csv_path in enumerate(csv_files):
        df = pd.read_csv(csv_path)
        # 过滤零温度
        df = df[df['T'] != 0].copy()

        if df.empty:
            print(f"警告: {csv_path.name} 无有效非零温度数据，跳过")
            continue

        # 按温度分组，取每个温度的最后一行（累计的最终值）
        last_rows = df.groupby('T').last().reset_index()

        # 计算拒绝率
        last_rows['rejection_rate'] = last_rows['T_reject'] / last_rows['T_Moves']

        # 取前 n_top 个最高温度
        top_rows = last_rows.nlargest(n_top, 'T')

        # 按温度升序排列（图表从左到右温度降低）
        top_rows = top_rows.sort_values('T', ascending=True)

        # 用文件名中的 runX 作为图例标签
        run_match = re.search(r'run(\d+)', csv_path.stem)
        label = f"run{run_match.group(1)}" if run_match else csv_path.stem

        plt.scatter(top_rows['T'], top_rows['rejection_rate'],
                    color=colors[idx], label=label, alpha=0.7, s=100,
                    edgecolors='k', linewidths=0.3)

        print(f"  [{idx}] {label}: {len(top_rows)} 个温度点")

    plt.xlabel('Temperature', fontsize=18)
    plt.ylabel('Rejection Rate (T_reject / T_Moves)', fontsize=18)
    # plt.title(f'Rejection Rate vs Temperature (Top {n_top} Temps, algo{algo})', fontsize=18)
    # plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    plt.legend(loc='upper right', fontsize=14)
    # plt.grid(True, alpha=0.9)
    # 温度通常跨越多个数量级，使用对数横轴
    plt.xscale('log')
    # 拒绝率范围在 [0,1] 之间
    plt.ylim(-0.02, 1.02)

    plt.tight_layout()
    filename = f"rejection_rates_top{n_top}_algo{algo}.png"
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
    parser.add_argument("--sample_step", type=int, default=100,
                        help="绘图时每多少点采样一次（默认100）")
    parser.add_argument("--rejection-rate", nargs='?', const='auto', default=None,
                        help="绘制拒绝率图：指定包含 curve_data_run*.csv 的目录路径，"
                         "会读取该目录下所有CSV文件并绘制在同一张散点图上。"
                         "纵轴=T_reject/T_Moves，横轴=温度，取前60个最高温度。")
    parser.add_argument("--rr-n-top", type=int, default=60,
                        help="与 --rejection-rate 配合使用...")
    # 新增
    parser.add_argument("--n_top", type=int, default=0,
                        help="额外绘制前 N 个数据点的曲线图（若超出总行数则绘制全部）")
    parser.add_argument("--n_back", type=int, default=0,
                        help="额外绘制后 N 个数据点的曲线图（若超出总行数则绘制全部）")
    parser.add_argument("--tune", nargs='?', const='auto', default=None,
                        help="调优模式：读取最新 tune_* 文件夹下所有 param_*/curve_data.csv 并绘图。"
                         "可指定具体路径，或留空自动选择最新。")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    results_curve_root = script_dir / "../results/curve_results"

    # ----- 调优模式（tune）-----
    if args.tune is not None:
        if args.tune == 'auto':
            tune_dir = find_latest_tune_dir(results_curve_root)
        else:
            tune_dir = Path(args.tune)
            if not tune_dir.is_dir():
                raise FileNotFoundError(f"调优目录不存在: {tune_dir}")

        print(f"调优模式: 读取 {tune_dir}")

        csv_files_tune = sorted(tune_dir.glob("param_*/curve_data.csv"))
        if not csv_files_tune:
            raise FileNotFoundError(f"在 {tune_dir} 中未找到任何 param_*/curve_data.csv 文件")

        print(f"找到 {len(csv_files_tune)} 个参数 CSV 文件")

        if args.output_dir:
            tune_output = Path(args.output_dir)
        else:
            tune_output = script_dir / "../results/curve_figures" / tune_dir.name
        tune_output.mkdir(parents=True, exist_ok=True)

        for csv_path in csv_files_tune:
            param_name = csv_path.parent.name  # e.g. "param_stagnation_limit100"
            output_subdir = tune_output / param_name
            output_subdir.mkdir(parents=True, exist_ok=True)

            algo_match = re.search(r'algo(\d+)', tune_dir.name)
            algo = int(algo_match.group(1)) if algo_match else 0

            process_single_csv(csv_path, output_subdir, suffix=param_name,
                               sample_step=args.sample_step, algo=algo,
                               n_top=args.n_top, n_back=args.n_back)

        print("调优模式绘图完成！")
        return

    # ----- 拒绝率图模式 -----
    if args.rejection_rate is not None:
        if args.rejection_rate == 'auto':
            # 自动使用最新时间戳文件夹
            latest_dir = find_latest_csv_dir(results_curve_root)
            rr_dir = latest_dir
            print(f"拒绝率图模式: 自动选择最新文件夹 {rr_dir}")
        else:
            rr_dir = Path(args.rejection_rate)
            if not rr_dir.is_dir():
                raise FileNotFoundError(f"拒绝率图路径不是有效目录: {rr_dir}")
        
        csv_files_rr = sorted(rr_dir.glob("curve_data_run*.csv"))
        if not csv_files_rr:
            raise FileNotFoundError(f"在 {rr_dir} 中未找到 curve_data_run*.csv 文件")
        
        print(f"拒绝率图模式: 从 {rr_dir} 读取到 {len(csv_files_rr)} 个CSV文件")
        
        # 从文件夹名提取 algo 编号（如果文件名中有 algo 信息）
        algo_match = re.search(r'algo(\d+)', rr_dir.name)
        algo_rr = int(algo_match.group(1)) if algo_match else 0
        
        # 输出目录
        if args.output_dir:
            rr_output = Path(args.output_dir)
        else:
            rr_output = script_dir / "../results/curve_figures" / rr_dir.name
        rr_output.mkdir(parents=True, exist_ok=True)
        
        plot_rejection_rates(csv_files_rr, rr_output, algo=algo_rr, n_top=args.rr_n_top)
        print("拒绝率图绘制完成！")
        return

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
        # 提取 algo 编号：优先用命令行参数，否则从文件名中提取
        algo_match = re.search(r'algo(\d+)', csv_path.stem)
        algo = int(algo_match.group(1)) if algo_match else 0

        # 调用处理函数
        process_single_csv(csv_path, output_subdir, suffix=csv_path.stem,
                   sample_step=args.sample_step, algo=algo,
                   n_top=args.n_top, n_back=args.n_back)

    print("全部绘图完成！")

if __name__ == "__main__":
    main()