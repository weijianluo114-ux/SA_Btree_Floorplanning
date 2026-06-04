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
def draw_layout(blocks, chip_width=None, output_image=None, show_labels=True, dpi=150):
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
    title = f'Floorplan Layout (Blocks: {len(blocks)})'
    if chip_width is not None:
        title += f' - Target W={chip_width} ({status})'
    ax.set_title(title)
    ax.grid(True, linestyle='--', alpha=0.5)

    # 保存或显示
    if output_image:
        Path(output_image).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_image, dpi=dpi, bbox_inches='tight')
        print(f"图片已保存至: {output_image}")
    else:
        plt.show()

def main():
    parser = argparse.ArgumentParser(description="绘制芯片布局规划的矩形图")
    parser.add_argument("--input_file", type=str, help="布局结果文件路径（.txt）")
    parser.add_argument("-o", "--output", type=str, default=None, help="输出图片路径（如 .png, .pdf）")
    parser.add_argument("--no_labels", action="store_true", help="不显示块名称标签")
    parser.add_argument("--dpi", type=int, default=300, help="输出图片分辨率（默认150）")
    args = parser.parse_args()

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
    draw_layout(blocks, chip_width, args.output, show_labels=not args.no_labels, dpi=args.dpi)

if __name__ == "__main__":
    main()