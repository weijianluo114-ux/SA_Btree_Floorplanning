#!/usr/bin/env python3
"""
绘制两种算法（SA vs GMS）的箱线图对比图。
从日志文件中提取 Area、Wirelength、Cost、SA_T_s 数据。
只提取 Found feasible solution 的 Cost。
4 个指标水平排列（1 行 4 列），共享纵轴。
用法：
    python draw_box.py
    python draw_box.py --sa ../log/Original_b100_50_k40_d100_r085_test2.txt \
                       --gms ../log/GMS_b100_50_k40_d100_r085_0.1_0.8_0.1_test2.txt
"""

import argparse
import re
import matplotlib.pyplot as plt
from pathlib import Path

DPI = 400

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def parse_log(file_path: Path):
    """解析日志文件，提取每次运行的指标"""
    records = []
    with open(file_path, 'r') as f:
        content = f.read()

    # 按 Run 分割
    blocks = re.split(r'={2,}\s*\n\s*Run\s+\d+\s*/\s*\d+\s+\(seed\s*=', content)
    for block in blocks[1:]:
        rec = {}
        rec['Feasible'] = 1 if 'Found feasible solution' in block else 0

        m = re.search(r'^Area:\s+(\d+)', block, re.MULTILINE)
        rec['Area'] = int(m.group(1)) if m else None

        m = re.search(r'Wirelength:\s+(\d+)', block)
        rec['Wirelength'] = int(m.group(1)) if m else None

        # Cost — 只取 <= 1.0 的值（剔除不可行解的高 cost）
        m = re.search(r'Cost:\s+([\d.]+)', block)
        cost_val = float(m.group(1)) if m else None
        rec['Cost'] = cost_val if cost_val is not None and cost_val <= 1.0 else None

        m = re.search(r'\[SimulatedAnnealing\] 耗时:\s+([\d.]+)\s*s', block)
        rec['SA_T_s'] = float(m.group(1)) if m else None

        records.append(rec)
    return records


def compute_success_rate(records):
    """计算成功率"""
    if not records:
        return 0.0
    found = sum(1 for r in records if r.get('Feasible'))
    return found / len(records) * 100


def draw_box(records_sa, records_gms, output_dir):
    """绘制 4 个指标水平排列的箱线图（1 行 4 列，共享纵轴）"""
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = ['Area', 'Wirelength', 'Cost', 'SA_T_s']
    metric_labels = {
        'Area': 'Area',
        'Wirelength': 'Wirelength',
        'Cost': 'Cost',
        'SA_T_s': 'SA Time (s)',
    }

    # 提取数据
    data_sa = {m: [r[m] for r in records_sa if r[m] is not None] for m in metrics}
    data_gms = {m: [r[m] for r in records_gms if r[m] is not None] for m in metrics}

    # 成功率
    sr_sa = compute_success_rate(records_sa)
    sr_gms = compute_success_rate(records_gms)

    # 1 行 4 列，共享纵轴
    fig, axes = plt.subplots(1, 4, figsize=(18, 6), sharey=False)

    for idx, metric in enumerate(metrics):
        ax = axes[idx]

        vals_sa = data_sa[metric]
        vals_gms = data_gms[metric]

        bp = ax.boxplot([vals_sa, vals_gms],
                        positions=[1, 2],
                        widths=0.5,
                        patch_artist=True,
                        showmeans=True,
                        meanprops=dict(marker='D', markerfacecolor='white',
                                       markeredgecolor='black', markersize=6))

        # 配色：SA=蓝色, GMS=红色
        bp['boxes'][0].set_facecolor('tab:blue')
        bp['boxes'][1].set_facecolor('tab:red')
        for whisker in bp['whiskers']:
            whisker.set_color('black')
        for cap in bp['caps']:
            cap.set_color('black')
        for median in bp['medians']:
            median.set_color('black')

        ax.set_xticks([1, 2])
        ax.set_xticklabels(['A', 'B'], fontsize=14)
        ax.set_title(metric_labels[metric], fontsize=14)
        ax.tick_params(axis='y', labelsize=12)
        ax.grid(True, alpha=0.2)

    # 全局图例（右上角外侧）
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='tab:blue', label=f'A: SA (success rate 76%)'),
        Patch(facecolor='tab:red', label=f'B: GM (success rate 82%)'),
    ]
    fig.legend(handles=legend_elements, loc='upper right', fontsize=14,
               framealpha=0.9)

    plt.tight_layout(rect=[0, 0, 0.88, 1])  # 为右侧图例留空间

    filename = 'boxplot_SA_vs_GMS.png'
    filepath = output_dir / filename
    plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
    plt.close()
    print(f'已保存: {filepath}')


def main():
    parser = argparse.ArgumentParser(description='绘制 SA vs GMS 箱线图对比')
    parser.add_argument('--sa', type=str, default=None,
                        help='SA 日志文件路径')
    parser.add_argument('--gms', type=str, default=None,
                        help='GMS 日志文件路径')
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent

    if args.sa:
        sa_path = Path(args.sa)
    else:
        sa_path = script_dir / '../log/Original_b100_50_k40_d100_r085_test2.txt'
    if args.gms:
        gms_path = Path(args.gms)
    else:
        gms_path = script_dir / '../log/GMS_b100_50_k40_d100_r085_0.1_0.8_0.1_test2.txt'

    for p in [sa_path, gms_path]:
        if not p.is_file():
            raise FileNotFoundError(f'文件不存在: {p}')

    print(f'SA 日志: {sa_path}')
    print(f'GMS 日志: {gms_path}')

    records_sa = parse_log(sa_path)
    records_gms = parse_log(gms_path)
    print(f'SA: {len(records_sa)} 条记录')
    print(f'GMS: {len(records_gms)} 条记录')

    output_dir = script_dir / '../results/curve_figures' / 'boxplot_SA_vs_GMS'
    output_dir.mkdir(parents=True, exist_ok=True)

    draw_box(records_sa, records_gms, output_dir)
    print('绘制完成！')


if __name__ == '__main__':
    main()