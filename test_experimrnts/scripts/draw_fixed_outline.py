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
    chip_width: 芯片宽度（若提供，则设置画布 x 轴范围 0..chip_width）
    output_image: 输出图片路径，若为 None 则显示窗口
    show_labels: 是否在每个矩形中央显示块名称
    """
    if not blocks:
        print("没有可绘制的块")
        return

    fig, ax = plt.subplots(figsize=(12, 10))

    # 确定画布范围
    max_x = chip_width if chip_width is not None else max(b[1] + b[3] for b in blocks)
    max_y = max(b[2] + b[4] for b in blocks)  # 最大 y + 高度

    # 绘制每个矩形
    for name, x, y, w, h in blocks:
        rect = patches.Rectangle(
            (x, y), w, h,
            linewidth=1.5, edgecolor='black', facecolor='lightblue', alpha=0.7
        )
        ax.add_patch(rect)

        if show_labels:
            # 在矩形中心放置名称
            cx = x + w / 2
            cy = y + h / 2
            ax.text(cx, cy, name, ha='center', va='center', fontsize=8, fontweight='bold')

    # 设置坐标轴
    ax.set_xlim(0, max_x * 1.02)  # 留一点边距
    ax.set_ylim(0, max_y * 1.02)
    ax.set_aspect('equal')        # 保持矩形比例不变形
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_title(f'Floorplan Layout (Blocks: {len(blocks)})')
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