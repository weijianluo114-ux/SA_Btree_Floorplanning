#!/usr/bin/env python3
"""
读取布局规划结果文件，绘制矩形块图。
文件格式：
    W: <width>                # 芯片宽度（可选，用于设置画布宽度）
    Wirelength : <value>      # 跳过
    Blocks: <num>             # 块数量
    <name> <x> <y> <p3> <p4> <rot>
        - rot = 1: 尺寸为 (height=p3, width=p4)
        - rot = 0: 尺寸为 (width=p3, height=p4)
"""

import argparse
import re
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

def parse_layout_file(file_path):
    """
    解析布局文件，返回：
        chip_width: 从第一行 W: 解析出的宽度，若不存在则为 None
        blocks: 列表，每个元素为 (name, x, y, width, height)
    """
    blocks = []
    chip_width = None

    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    # 解析第一行（可能为 "W:444"）
    if lines and lines[0].startswith('W:'):
        match = re.match(r'W:\s*(\d+)', lines[0])
        if match:
            chip_width = int(match.group(1))
        lines = lines[1:]  # 移除第一行

    # 跳过第二行（Wirelength），如果存在
    if lines and 'Wirelength' in lines[0]:
        lines = lines[1:]

    # 解析第三行 "Blocks:100"
    if lines and lines[0].startswith('Blocks:'):
        match = re.match(r'Blocks:\s*(\d+)', lines[0])
        if match:
            num_blocks = int(match.group(1))
        lines = lines[1:]
    else:
        num_blocks = None

    # 解析每个块
    for line in lines:
        parts = line.split()
        if len(parts) != 6:
            continue  # 忽略不符合的行
        name = parts[0]
        x = int(parts[1])
        y = int(parts[2])
        p3 = int(parts[3])
        p4 = int(parts[4])
        rot = int(parts[5])

        if rot == 1:
            height = p3
            width = p4
        else:  # rot == 0
            width = p3
            height = p4

        blocks.append((name, x, y, width, height))

    # 可选：检查块数量是否匹配
    if num_blocks is not None and len(blocks) != num_blocks:
        print(f"警告: 文件声明有 {num_blocks} 个块，但实际解析到 {len(blocks)} 个")

    return chip_width, blocks
def draw_layout(blocks, chip_width=None, output_image=None, show_labels=True, dpi=300, algo=0):
    """
    绘制矩形布局。
    blocks: 列表 of (name, x, y, width, height)
    chip_width: 目标芯片宽度/高度（正方形）。若提供，则比较实际布局是否超出。
    output_image: 输出图片路径，若为 None 则显示窗口
    show_labels: 是否在每个矩形中央显示块名称
    """
    if not blocks:
        print("没有可绘制的块")
        return

    fig, ax = plt.subplots(figsize=(12, 10))

    # 计算实际最大 x 和 y（块右下角坐标）
    max_x = max(b[1] + b[3] for b in blocks)  # x + width
    max_y = max(b[2] + b[4] for b in blocks)  # y + height

    if chip_width is not None:
        target = chip_width
        # 判断是否超出目标
        if max_x > target or max_y > target:
            line_color = 'red'
            status = "not fix target"
            # 超出时，画布范围取实际最大值与目标中的较大者，以便看到超出部分
            limit = max(max_x, max_y, target)
        else:
            line_color = 'green'
            status = "fix target"
            # 未超出时，画布范围取目标值（可以留少量边距，但为了清晰直接取target）
            limit = target

        # 画垂直线 x = target 和水平线 y = target
        ax.axvline(x=target, color=line_color, linestyle='--', linewidth=2,
                   label=f'Target W={target} ({status})')
        ax.axhline(y=target, color=line_color, linestyle='--', linewidth=2)

        # 设置坐标轴范围（0 到 limit）
        ax.set_xlim(0, limit)
        ax.set_ylim(0, limit)
    else:
        status = "no target"
        # 未提供目标，使用实际最大值并留一点边距
        limit = max(max_x, max_y)
        ax.set_xlim(0, limit * 1.02)
        ax.set_ylim(0, limit * 1.02)

    # 绘制每个矩形
    for name, x, y, w, h in blocks:
        rect = patches.Rectangle(
            (x, y), w, h,
            linewidth=1.5, edgecolor='black', facecolor='lightblue', alpha=0.7
        )
        ax.add_patch(rect)

        if show_labels:
            cx = x + w / 2
            cy = y + h / 2
            ax.text(cx, cy, name, ha='center', va='center', fontsize=8, fontweight='bold')

    ax.set_aspect('equal')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    title = f'Floorplan Layout algo{algo} (Blocks: {len(blocks)})'
    if chip_width is not None:
        title += f' - Target W={chip_width} ({status})'
    ax.set_title(title)
    ax.grid(True, linestyle='--', alpha=0.5)

    # 隐藏上框线和右框线
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # 保存或显示
    if output_image:
        Path(output_image).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_image, dpi=dpi, bbox_inches='tight')
        print(f"图片已保存至: {output_image}")
    else:
        plt.show()

def draw_batch_floorplans(num_hardblocks, white_space_ratio, num_runs, algo, output_dir_fig=None):
    """
    批量模式：根据参数定位输出目录，自动找到所有 .floorplan 文件并逐一绘制。
    若有时间戳则取最新且相同的一组，否则绘制全部。
    """
    script_dir = Path(__file__).resolve().parent
    ratio_str = str(white_space_ratio).replace('.', '_')
    algo_tag = f"_algo{algo}"

    # 构建输出目录路径（与 test_scripts.py 保持一致）
    dir_name = f"test_{num_hardblocks}blocks_ratio_{ratio_str}_total_{num_runs}{algo_tag}"
    output_dir = (script_dir / "../output" / dir_name).resolve()

    if not output_dir.exists():
        raise FileNotFoundError(f"输出目录不存在: {output_dir}")

    # 查找所有 .floorplan 文件
    floorplan_files = list(output_dir.glob("*.floorplan"))
    if not floorplan_files:
        raise FileNotFoundError(f"在 {output_dir} 中未找到任何 .floorplan 文件")

    # 提取时间戳并按时间戳分组
    ts_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2})")
    ts_groups = {}       # 时间戳字符串 -> [文件列表]
    files_no_ts = []     # 无时间戳的文件

    for f in floorplan_files:
        m = ts_pattern.search(f.stem)
        if m:
            ts = m.group(1)
            ts_groups.setdefault(ts, []).append(f)
        else:
            files_no_ts.append(f)

    # 决定要处理的文件
    if ts_groups:
        latest_ts = max(ts_groups.keys())
        selected_files = sorted(ts_groups[latest_ts])
        print(f"找到 {len(ts_groups)} 组不同时间戳，使用最新的: {latest_ts} ({len(selected_files)} 个文件)")
    else:
        selected_files = sorted(files_no_ts)
        print(f"未检测到时间戳，使用全部 {len(selected_files)} 个文件")

    # 输出图片目录
    if output_dir_fig is None:
        base_fig_dir = script_dir / "../results/floor_plan_figures" / dir_name
    else:
        base_fig_dir = Path(output_dir_fig)
    base_fig_dir.mkdir(parents=True, exist_ok=True)

    # 逐一解析并绘制
    for fp in selected_files:
        chip_width, blocks = parse_layout_file(str(fp))
        if not blocks:
            print(f"⚠ 跳过 {fp.name}：无有效块数据")
            continue

        out_img = base_fig_dir / f"{fp.stem}.png"
        draw_layout(blocks, chip_width, output_image=str(out_img), show_labels=True, dpi=300)
        print(f"✓ {fp.name} → {out_img}")

    print(f"\n全部 floorplan 绘制完成！图片保存至: {base_fig_dir}")

def main():
    parser = argparse.ArgumentParser(description="绘制芯片布局规划的矩形图")
    parser.add_argument("--input_file", type=str, 
                        help="布局结果文件路径（.txt）")
    parser.add_argument("-o", "--output", type=str, default=None, 
                        help="输出图片路径（如 .png, .pdf）")
    parser.add_argument("--no_labels", action="store_true", 
                        help="不显示块名称标签")
    parser.add_argument("--dpi", type=int, default=300, 
                        help="输出图片分辨率（默认300）")
    parser.add_argument("--batch", action="store_true",
                        help="批量模式：自动读取输出目录下所有 .floorplan 文件并绘图")
    parser.add_argument("--num_hardblocks", type=int, default=None,
                        help="硬模块数量，如 100")
    parser.add_argument("--white_space_ratio", type=float, default=None,
                        help="空白率，如 0.1")
    parser.add_argument("--num_runs", type=int, default=None,
                        help="运行次数，如 1")
    parser.add_argument("-a", "--algo", type=int, default=0,
                        help="算法模式: 0=原始算法, 1=GMS (默认0)")
    args = parser.parse_args()

    # ===== 批量模式 =====
    if args.batch:
        if args.num_hardblocks is None or args.white_space_ratio is None or args.num_runs is None:
            print("错误: --batch 模式需要指定 --num_hardblocks, --white_space_ratio, --num_runs",
                  file=sys.stderr)
            sys.exit(1)
        draw_batch_floorplans(args.num_hardblocks, args.white_space_ratio,
                              args.num_runs, args.algo)
        return

    # ===== 单文件模式（原有） =====
    if args.input_file is None:
        print("错误: 请指定 --input_file（单文件模式）或使用 --batch（批量模式）")
        sys.exit(1)

    # 解析文件
    chip_width, blocks = parse_layout_file(args.input_file)
    if not blocks:
        print("错误: 未能解析任何块，请检查文件格式")
        return

    print(f"解析到 {len(blocks)} 个块")
    if chip_width:
        print(f"芯片宽度: {chip_width}")
    else:
        print("未提供芯片宽度，将根据块的最大 x+width 自动计算")

    # 绘图
    draw_layout(blocks, chip_width, args.output, show_labels=not args.no_labels, dpi=args.dpi, algo=args.algo)

if __name__ == "__main__":
    main()