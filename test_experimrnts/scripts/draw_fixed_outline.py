#!/usr/bin/env python3
"""
读取布局规划结果文件，绘制矩形块图和对应的 B*-tree 图。
支持两种模式：
  1. 批量模式（默认）：根据 --blocks, --ratio, --num_runs, --algo 定位输出目录
  2. 单文件模式：通过 --floorplan 和 --btree 指定具体文件

用法示例:
    # 批量模式
    python draw_fixed_outline.py --blocks 100 --ratio 0.1 --num_runs 30 --algo 0 --max_read 5

    # 单文件模式
    python draw_fixed_outline.py --floorplan ../output/xxx/run1_2026-06-09_12:00:00.floorplan
"""

import argparse
import re
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D

# ==============================================================
#  第一部分：解析 .floorplan 文件
# ==============================================================

def parse_floorplan_file(file_path):
    """
    解析 .floorplan 文件，返回 (chip_width, blocks)
    blocks: list of (name, x, y, width, height)
    """
    blocks = []
    chip_width = None

    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    if lines and lines[0].startswith('W:'):
        match = re.match(r'W:\s*(\d+)', lines[0])
        if match:
            chip_width = int(match.group(1))
        lines = lines[1:]

    if lines and 'Wirelength' in lines[0]:
        lines = lines[1:]

    if lines and lines[0].startswith('Blocks:'):
        lines = lines[1:]

    for line in lines:
        parts = line.split()
        if len(parts) != 6:
            continue
        name = parts[0]
        x = int(parts[1])
        y = int(parts[2])
        p3 = int(parts[3])
        p4 = int(parts[4])
        rot = int(parts[5])
        if rot == 1:
            height, width = p3, p4
        else:
            width, height = p3, p4
        blocks.append((name, x, y, width, height))

    return chip_width, blocks


# ==============================================================
#  第二部分：解析 .Btree 文件
# ==============================================================

def parse_btree_file(file_path, num_blocks):
    """
    解析 .Btree 文件，返回 (root_id, children_list)
    children_list: list of (left_child, right_child)，索引即节点 ID
    """
    root_id = -1
    # children[i] = (left, right)，-1 表示空
    children = [(-1, -1) for _ in range(num_blocks)]

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("Root:"):
                root_id = int(line.split()[1])
                continue
            parts = line.split()
            if len(parts) == 4:
                node_id = int(parts[0])
                # parent = int(parts[1])   # 父节点信息不需要用于绘图
                left = int(parts[2])
                right = int(parts[3])
                children[node_id] = (left, right)

    return root_id, children


# ==============================================================
#  第三部分：B*-tree 布局与绘图
# ==============================================================

def compute_tree_layout(root_id, children):
    """
    计算二叉树的 (x, y) 位置用于绘图。
    返回: dict {node_id: (x, y)}
    
    策略：
    - y = -depth（根在最上方）
    - x 由中序遍历分配（左子树在左，右子树在右）
    """
    if root_id < 0:
        return {}

    # 1) 计算每个节点的深度
    depth = {root_id: 0}
    stack = [root_id]
    while stack:
        node = stack.pop()
        left, right = children[node]
        if left != -1:
            depth[left] = depth[node] + 1
            stack.append(left)
        if right != -1:
            depth[right] = depth[node] + 1
            stack.append(right)

    # 2) 中序遍历分配 x 坐标
    x_pos = {}
    x_counter = [0]  # 用列表以便在嵌套函数中修改

    def inorder(node):
        if node == -1:
            return
        left, right = children[node]
        inorder(left)
        x_pos[node] = x_counter[0]
        x_counter[0] += 1
        inorder(right)

    inorder(root_id)

    # 3) 组合 (x, y)
    pos = {}
    for node in x_pos:
        pos[node] = (x_pos[node], -depth[node])

    return pos


def draw_btree(root_id, children, block_names, output_image=None, dpi=300):
    """
    绘制 B*-tree（二叉树结构图）。
    block_names: list of str，节点 ID -> 显示名称（如 "sb0", "sb1"）
    """
    pos = compute_tree_layout(root_id, children)
    if not pos:
        print("  二叉树为空，跳过")
        return

    # 计算树的宽度（水平跨度）和深度（垂直跨度），用于设置图像比例
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    tree_width = max(xs) - min(xs) if xs else 1
    tree_depth = max(ys) - min(ys) if ys else 1
    # 紧凑布局：缩小尺寸系数使连线更短、整体更紧凑
    fig_w = max(5, tree_width * 0.19)
    fig_h = max(5, tree_depth * 1.3)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    # 绘制边（线宽稍细，更紧凑）
    for node, (x, y) in pos.items():
        left, right = children[node]
        for child in (left, right):
            if child != -1 and child in pos:
                cx, cy = pos[child]
                ax.plot([x, cx], [y, cy], 'k-', linewidth=1.0)

    # 绘制节点（圆圈内刚好容纳文字）
    for node, (x, y) in pos.items():
        name = block_names[node] if node < len(block_names) else f"sb{node}"
        ax.plot(x, y, 'o', markersize=20, color='lightblue',
            markeredgecolor='black', markeredgewidth=1.0, zorder=3)
        ax.text(x, y, name, ha='center', va='center', fontsize=6, fontweight='bold', zorder=4)

    ax.set_aspect('auto')
    ax.axis('off')
    ax.set_title(f"B*-tree (Root: sb{root_id}, Nodes: {len(pos)})")

    if output_image:
        Path(output_image).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_image, dpi=dpi, bbox_inches='tight')
        print(f"  二叉树图已保存至: {output_image}")
    else:
        plt.show()
    plt.close()


# ==============================================================
#  第四部分：绘制 floorplan 矩形图
# ==============================================================

def draw_floorplan(blocks, chip_width=None, output_image=None,
                   show_labels=True, dpi=300, algo=0):
    """绘制矩形布局图。"""
    if not blocks:
        print("  没有可绘制的块")
        return

    fig, ax = plt.subplots(figsize=(12, 10))

    max_x = max(b[1] + b[3] for b in blocks)
    max_y = max(b[2] + b[4] for b in blocks)

    if chip_width is not None:
        target = chip_width
        if max_x > target or max_y > target:
            line_color = 'red'
            status = "超出目标"
            limit = max(max_x, max_y, target)
        else:
            line_color = 'green'
            status = "满足目标"
            limit = target
        ax.axvline(x=target, color=line_color, linestyle='--', linewidth=2,
                   label=f'Target W={target} ({status})')
        ax.axhline(y=target, color=line_color, linestyle='--', linewidth=2)
        ax.set_xlim(0, limit)
        ax.set_ylim(0, limit)
    else:
        limit = max(max_x, max_y)
        ax.set_xlim(0, limit * 1.02)
        ax.set_ylim(0, limit * 1.02)

    for name, x, y, w, h in blocks:
        rect = patches.Rectangle(
            (x, y), w, h,
            linewidth=1.5, edgecolor='black', facecolor='lightblue', alpha=0.7
        )
        ax.add_patch(rect)
        if show_labels:
            ax.text(x + w / 2, y + h / 2, name,
                    ha='center', va='center', fontsize=8, fontweight='bold')

    ax.set_aspect('equal')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    title = f'Floorplan (algo{algo}, {len(blocks)} blocks)'
    if chip_width is not None:
        title += f' - Target W={chip_width} ({status})'
    ax.set_title(title)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if output_image:
        Path(output_image).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_image, dpi=dpi, bbox_inches='tight')
        print(f"  Floorplan 图已保存至: {output_image}")
    else:
        plt.show()
    plt.close()


# ==============================================================
#  第五部分：批量处理
# ==============================================================

def get_output_dir(script_dir, blocks, ratio, num_runs, algo):
    """根据参数构建输出目录路径。"""
    ratio_str = str(ratio).replace('.', '_')
    dir_name = f"test_{blocks}blocks_ratio_{ratio_str}_total_{num_runs}_algo{algo}"
    return (script_dir / "../output" / dir_name).resolve()


def get_sorted_file_pairs(output_dir, max_read=None):
    """
    从 output_dir 中查找所有 .floorplan 和对应的 .Btree 文件。
    按文件名排序（时间戳），返回 list of (floorplan_path, btree_path)。
    max_read: 最多读取的文件对数（从第一对开始）。
    """
    fp_files = sorted(output_dir.glob("*.floorplan"))

    pairs = []
    for fp in fp_files:
        # 对应的 .Btree 文件名：替换后缀
        btree_path = fp.with_suffix(".Btree")
        if btree_path.exists():
            pairs.append((fp, btree_path))
        else:
            print(f"  警告: {fp.name} 无对应的 .Btree 文件，跳过")
            continue

    if max_read is not None and max_read > 0:
        pairs = pairs[:max_read]

    return pairs


def run_batch(args):
    """批量处理主逻辑。"""
    script_dir = Path(__file__).resolve().parent
    output_dir = get_output_dir(script_dir, args.blocks, args.ratio,
                                args.num_runs, args.algo)

    if not output_dir.exists():
        print(f"错误: 输出目录不存在: {output_dir}", file=sys.stderr)
        sys.exit(1)

    pairs = get_sorted_file_pairs(output_dir, args.max_read)
    if not pairs:
        print(f"错误: 在 {output_dir} 中未找到有效的 .floorplan + .Btree 文件对",
              file=sys.stderr)
        sys.exit(1)

    print(f"找到 {len(pairs)} 对文件，输出目录: {output_dir}")

    # 图片输出目录
    ratio_str = str(args.ratio).replace('.', '_')
    dir_name = f"test_{args.blocks}blocks_ratio_{ratio_str}_total_{args.num_runs}_algo{args.algo}"
    fig_dir = script_dir / "../results/floor_plan_figures" / dir_name
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 预生成块名称列表（用于 B-tree 绘图）
    block_names = [f"sb{i}" for i in range(args.blocks)]

    for idx, (fp_path, bt_path) in enumerate(pairs, start=1):
        stem = fp_path.stem  # 如 "run1_2026-06-09_12:00:00"
        print(f"\n[{idx}/{len(pairs)}] 处理 {stem}")

        # --- 绘制 Floorplan ---
        chip_width, blocks = parse_floorplan_file(str(fp_path))
        if blocks:
            fp_img = fig_dir / f"{stem}_floorplan.png"
            draw_floorplan(blocks, chip_width, output_image=str(fp_img),
                           show_labels=True, dpi=args.dpi, algo=args.algo)
        else:
            print(f"  跳过 Floorplan: 无有效块数据")

        # --- 绘制 B-tree ---
        root_id, children = parse_btree_file(str(bt_path), args.blocks)
        if root_id >= 0:
            bt_img = fig_dir / f"{stem}_btree.png"
            draw_btree(root_id, children, block_names,
                       output_image=str(bt_img), dpi=args.dpi)
        else:
            print(f"  跳过 B-tree: 无效根节点")

    print(f"\n全部绘制完成！图片保存至: {fig_dir}")


# ==============================================================
#  第六部分：主函数
# ==============================================================

def main():
    parser = argparse.ArgumentParser(
        description="绘制芯片布局规划的矩形图及对应的 B*-tree 图"
    )

    # --- 批量模式参数 ---
    parser.add_argument("--blocks", type=int, default=100,
                        help="硬模块数量，如 100")
    parser.add_argument("--ratio", type=float, default=0.1,
                        help="空白率，如 0.1")
    parser.add_argument("--num_runs", type=int, default=None,
                        help="运行次数，如 30")
    parser.add_argument("-a", "--algo", type=int, default=0,
                        help="算法模式: 0=SA, 1=GMS, ... (默认0)")
    parser.add_argument("--max_read", type=int, default=None,
                        help="最多读取的文件对数（从 run1 开始）")

    # --- 单文件模式参数 ---
    parser.add_argument("--floorplan", type=str, default=None,
                        help="单文件模式: .floorplan 文件路径")
    parser.add_argument("--btree", type=str, default=None,
                        help="单文件模式: .Btree 文件路径（可选，不提供则不画树）")

    # --- 通用参数 ---
    parser.add_argument("--dpi", type=int, default=300,
                        help="输出图片分辨率（默认300）")
    parser.add_argument("--no_labels", action="store_true",
                        help="不显示块名称标签")

    args = parser.parse_args()

    # ===== 批量模式（同时提供了 --blocks 和 --ratio）=====
    if args.blocks is not None and args.ratio is not None:
        # num_runs 默认 1
        if args.num_runs is None:
            args.num_runs = 1
        run_batch(args)
        return

    # ===== 单文件模式 =====
    if args.floorplan is not None:
        fp_path = Path(args.floorplan)
        if not fp_path.exists():
            print(f"错误: 文件不存在: {fp_path}", file=sys.stderr)
            sys.exit(1)

        # 自动推断 blocks 数量
        chip_width, blocks = parse_floorplan_file(str(fp_path))
        if not blocks:
            print("错误: 未能解析任何块，请检查文件格式", file=sys.stderr)
            sys.exit(1)

        num_blocks = len(blocks)
        block_names = [f"sb{i}" for i in range(num_blocks)]

        # 绘制 Floorplan
        fp_img = None  # 不保存，直接显示
        draw_floorplan(blocks, chip_width, output_image=None,
                       show_labels=not args.no_labels, dpi=args.dpi)

        # 绘制 B-tree（如果有对应的 .Btree 文件）
        if args.btree:
            bt_path = Path(args.btree)
        else:
            bt_path = fp_path.with_suffix(".Btree")

        if bt_path.exists():
            root_id, children = parse_btree_file(str(bt_path), num_blocks)
            if root_id >= 0:
                draw_btree(root_id, children, block_names,
                           output_image=None, dpi=args.dpi)
        else:
            print("未找到对应的 .Btree 文件，跳过树图绘制")

        return

    # ===== 参数不足 =====
    print("错误: 请提供 --blocks 和 --ratio（批量模式），或 --floorplan（单文件模式）",
          file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()