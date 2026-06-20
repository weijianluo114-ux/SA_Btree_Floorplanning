#!/usr/bin/env python3
"""
绘制总算法对比折线图（读取 总算法对比.xlsx）
- 横轴：6 种算法（排除 GM_Dmatrix_SA）
- 纵轴：6 个指标分别绘图
- 3 条线：n100（实线+圆点）、n200（虚线+方块）、n300（点划线+菱形）
- 每种指标使用不同颜色
- 输出 EPS + PNG 到 ./results/total_results/figure/
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from pathlib import Path
import numpy as np

# ──────────────────────────────────────────────
# 全局设置
# ──────────────────────────────────────────────
DPI = 400
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

# ──────────────────────────────────────────────
# 路径配置
# ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
EXCEL_PATH = SCRIPT_DIR / "../results/total_results/总算法对比.xlsx"
OUTPUT_DIR = SCRIPT_DIR / "../results/total_results/figure"

# 算法名称（按表格原始顺序，排除 GM_Dmatrix_SA）
ALGORITHMS = [
    "Classical_SA",
    "GM_SA",
    "Fast_SA",
    "GM_Fast_SA",
    "SawTooth_Fast_SA",
    "GM_SawTooth_Fast_SA",
]

# 算法显示名（用于横轴标签）
ALGO_LABELS = [
    "Classical\nSA",
    "GM\nSA",
    "Fast\nSA",
    "GM\nFastSA",
    "SawTooth\nFastSA",
    "GM\nSawTooth",
]

# 6 个要绘制的指标
METRICS = ["Area", "Wirelength", "R", "Cost", "Time(s)", "Success Rate(%)"]

# 不同 n 的线型配置
N_CONFIG = {
    100: {'linestyle': '-',  'marker': 'o', 'markersize': 8, 'label': 'n=100'},
    200: {'linestyle': '--', 'marker': 's', 'markersize': 7, 'label': 'n=200'},
    300: {'linestyle': '-.', 'marker': 'D', 'markersize': 7, 'label': 'n=300'},
}

# 指标对应的颜色
COLOR_MAP = {
    "Area":           '#E41A1C',   # 红
    "Wirelength":     '#377EB8',   # 蓝
    "R":              '#4DAF4A',   # 绿
    "Cost":           '#984EA3',   # 紫
    "Time(s)":        '#FF7F00',   # 橙
    "Success Rate(%)": '#A65628',  # 棕
}

# 纵轴标签
YLABEL_MAP = {
    "Area":           "Area",
    "Wirelength":     "Wirelength",
    "R":              "R (Aspect Ratio)",
    "Cost":           "Cost",
    "Time(s)":        "Time (s)",
    "Success Rate(%)": "Success Rate",
}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. 读取 Excel ──
    print(f"正在读取: {EXCEL_PATH}")
    xls = pd.ExcelFile(EXCEL_PATH)
    print(f"工作表: {xls.sheet_names}")

    sheet_name = xls.sheet_names[0]
    df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
    print(f"\n工作表 '{sheet_name}' 形状: {df.shape}")
    print(f"列名: {df.columns.tolist()}")

    col_list = df.columns.tolist()

    # 识别 dataset 列和 index 列
    dataset_col = None
    index_col = None
    for c in col_list:
        cl = str(c).strip().lower()
        if 'dataset' in cl or '数据' in cl:
            dataset_col = c
        elif 'index' in cl or '指标' in cl:
            index_col = c

    if dataset_col is None:
        dataset_col = col_list[0]
    if index_col is None:
        index_col = col_list[1]

    print(f"数据集列: '{dataset_col}', 指标列: '{index_col}'")

    # ★★★ 关键修复：建立精确的列名→算法名映射 ★★★
    # 用 ALGORITHMS 中的名字去精确匹配列名
    algo_col_map = {}  # {algo_name: column_name_in_excel}
    for algo in ALGORITHMS:
        # 在列名中精确匹配
        for c in col_list:
            if c == dataset_col or c == index_col:
                continue
            cl = str(c).strip().lower()
            if 'dmatrix' in cl or 'd_matrix' in cl:
                continue
            # 精确匹配（忽略大小写和下划线差异）
            if algo.lower().replace('_', '') == cl.lower().replace('_', ''):
                algo_col_map[algo] = c
                break
            # 备选：algo 是列名的子串但反过来不行（避免 gm_sa 匹配 gm_sawtooth）
            if algo.lower() == cl.lower():
                algo_col_map[algo] = c
                break

    print(f"\n算法列映射:")
    for algo, col in algo_col_map.items():
        print(f"  {algo} -> '{col}'")

    algo_columns = list(algo_col_map.values())
    print(f"算法列 ({len(algo_columns)} 个): {algo_columns}")

    # ── 2. 解析数据为 data[n][algo][metric] = value ──
    data = {}  # {n: {algo: {metric: value}}}

    for _, row in df.iterrows():
        ds = str(row[dataset_col]).strip().lower()
        n_val = None
        for n in [100, 200, 300]:
            if str(n) in ds:
                n_val = n
                break
        if n_val is None:
            continue

        metric_name = str(row[index_col]).strip()
        # 归一化指标名（处理 "Success Rate(%)  (%)" 这种情况）
        for std_metric in METRICS:
            if std_metric.lower().replace(' ', '').replace('(', '').replace(')', '').replace('%', '') \
               in metric_name.lower().replace(' ', '').replace('(', '').replace(')', '').replace('%', ''):
                metric_name = std_metric
                break

        if n_val not in data:
            data[n_val] = {}

        for algo in ALGORITHMS:
            col_name = algo_col_map.get(algo)
            if col_name is None:
                continue
            try:
                value = float(row[col_name])
            except (ValueError, TypeError):
                value = None

            if algo not in data[n_val]:
                data[n_val][algo] = {}
            data[n_val][algo][metric_name] = value

    # ── 3. 打印解析结果 ──
    print("\n" + "=" * 60)
    print("解析结果:")
    print("=" * 60)
    for n in sorted(data.keys()):
        print(f"\nn={n}:")
        for algo in ALGORITHMS:
            if algo in data[n]:
                print(f"  {algo}: {data[n][algo]}")
            else:
                print(f"  {algo}: (未找到)")

    # ── 4. 绘制每个指标的独立折线图 ──
    for metric in METRICS:
        fig, ax = plt.subplots(figsize=(12, 6.5))
        color = COLOR_MAP.get(metric, '#000000')

        x_pos = np.arange(len(ALGORITHMS))

        for n in sorted(data.keys()):
            cfg = N_CONFIG[n]

            values = []
            for algo in ALGORITHMS:
                if algo in data[n] and metric in data[n][algo]:
                    val = data[n][algo][metric]
                    values.append(val if val is not None else np.nan)
                else:
                    values.append(np.nan)

            offset = (sorted(data.keys()).index(n) - 1) * 0.12
            ax.plot(x_pos + offset, values,
                    color=color,
                    linestyle=cfg['linestyle'],
                    marker=cfg['marker'],
                    markersize=cfg['markersize'],
                    linewidth=2.0,
                    markerfacecolor=color,
                    markeredgecolor='black',
                    markeredgewidth=0.5,
                    label=cfg['label'],
                    alpha=0.85)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(ALGO_LABELS, fontsize=12)
        ax.set_xlabel('Algorithm', fontsize=14)
        ax.set_ylabel(YLABEL_MAP.get(metric, metric), fontsize=14)

        if metric == "Success Rate(%)":
            ax.yaxis.set_major_formatter(
                FuncFormatter(lambda x, _: f'{x*100:.0f}%' if x < 1 else f'{x:.0f}%')
            )

        ax.set_title(f'{metric}', fontsize=15, fontweight='bold')
        ax.legend(fontsize=12, loc='best')
        ax.grid(True, alpha=0.3, linestyle=':')

        plt.tight_layout()

        safe_name = metric.replace('(', '').replace(')', '').replace('%', 'Percent')
        eps_path = OUTPUT_DIR / f'{safe_name}_comparison.eps'
        png_path = OUTPUT_DIR / f'{safe_name}_comparison.png'

        plt.savefig(eps_path, dpi=DPI, format='eps', bbox_inches='tight')
        plt.savefig(png_path, dpi=DPI, format='png', bbox_inches='tight')
        print(f"已保存: {eps_path}")
        plt.close()

    # ── 5. 绘制汇总总图（2行×3列） ──
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    axes = axes.flatten()
    x_pos = np.arange(len(ALGORITHMS))
    n_sorted = sorted(data.keys())

    for idx, metric in enumerate(METRICS):
        ax = axes[idx]
        color = COLOR_MAP.get(metric, '#000000')

        for n in n_sorted:
            cfg = N_CONFIG[n]
            values = []
            for algo in ALGORITHMS:
                if algo in data[n] and metric in data[n][algo]:
                    val = data[n][algo][metric]
                    values.append(val if val is not None else np.nan)
                else:
                    values.append(np.nan)

            offset = (n_sorted.index(n) - 1) * 0.12
            ax.plot(x_pos + offset, values,
                    color=color,
                    linestyle=cfg['linestyle'],
                    marker=cfg['marker'],
                    markersize=cfg['markersize'],
                    linewidth=1.8,
                    markerfacecolor=color,
                    markeredgecolor='black',
                    markeredgewidth=0.5,
                    label=cfg['label'],
                    alpha=0.85)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(ALGO_LABELS, fontsize=9, rotation=15, ha='right')
        ax.set_ylabel(YLABEL_MAP.get(metric, metric), fontsize=11)
        ax.set_title(metric, fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle=':')
        ax.legend(fontsize=10, loc='best')

    plt.tight_layout()

    eps_path = OUTPUT_DIR / 'all_metrics_comparison.eps'
    png_path = OUTPUT_DIR / 'all_metrics_comparison.png'
    plt.savefig(eps_path, dpi=DPI, format='eps', bbox_inches='tight')
    plt.savefig(png_path, dpi=DPI, format='png', bbox_inches='tight')
    print(f"已保存: {eps_path}")

    print(f"\n✅ 完成！共生成 {len(METRICS) + 1} 张图 → {OUTPUT_DIR}")


if __name__ == '__main__':
    main()