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
import numpy as np
import matplotlib.cm as cm
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
#  第1.5部分：解析 .pl 和 .nets 文件（新增）
# ==============================================================

def parse_pl_file(file_path):
    """
    解析 .pl 文件，返回引脚坐标字典 {pin_name: (x, y)}。
    .pl 文件格式：每行 "pin_name x y"
    """
    pins = {}
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                name = parts[0]
                x = int(parts[1])
                y = int(parts[2])
                pins[name] = (x, y)
    return pins


def parse_nets_file(file_path):
    """
    解析 .nets 文件，返回网表列表。
    返回: list of list of str，每个子列表是一个网表中的所有元素（引脚/模块名）
    
    .nets 文件格式：
        NumNets : N
        NumPins : M
        NetDegree : D
        elem1
        elem2
        ...
    """
    nets = []
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    # 跳过文件头 (NumNets / NumPins 行)
    while lines and (lines[0].startswith('NumNets') or lines[0].startswith('NumPins')):
        lines = lines[1:]

    i = 0
    while i < len(lines):
        if lines[i].startswith('NetDegree'):
            degree = int(lines[i].split(':')[1].strip())
            i += 1
            net = []
            for _ in range(degree):
                if i < len(lines):
                    net.append(lines[i])
                    i += 1
            nets.append(net)
        else:
            i += 1

    return nets


def _build_block_dict(blocks):
    """
    从 blocks list 构建 {name: (x, y, w, h)} 字典。
    """
    return {b[0]: (b[1], b[2], b[3], b[4]) for b in blocks}


def _get_net_positions(net_elements, block_dict, pin_dict):
    """
    获取网表中各元素的位置坐标。
    - 模块 (sb*) 取其中心坐标
    - 引脚 (p*) 取 .pl 中的坐标
    返回: list of (x, y)
    """
    positions = []
    for elem in net_elements:
        if elem in block_dict:
            bx, by, bw, bh = block_dict[elem]
            positions.append((bx + bw / 2, by + bh / 2))
        elif elem in pin_dict:
            positions.append(pin_dict[elem])
    return positions


def draw_nets_on_floorplan(ax, nets, block_dict, pin_dict, max_nets=None):
    """
    在已存在的 matplotlib Axes 上叠加绘制网表连线。
    每个网表使用不同的颜色（循环使用 tab20 色表）。
    
    参数:
        ax: matplotlib Axes 对象
        nets: list of list of str，网表列表
        block_dict: {name: (x, y, w, h)} 模块位置字典
        pin_dict: {name: (x, y)} 引脚坐标字典
        max_nets: 最多绘制的网表数（None 表示全部）
    """
    num_nets = len(nets)
    if num_nets == 0:
        return

    # 使用 tab20 色表循环（20 种不同颜色）
    colors = cm.tab20(np.linspace(0, 1, 20))
    drawn = 0

    for idx, net in enumerate(nets):
        if max_nets is not None and drawn >= max_nets:
            break

        positions = _get_net_positions(net, block_dict, pin_dict)
        if len(positions) < 2:
            continue

        color = colors[drawn % len(colors)]
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]

        # 小度数网表 (2~4) 使用完全连接（两两连接）
        # 大度数网表使用链式连接避免过于杂乱
        if len(positions) <= 4:
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    ax.plot([positions[i][0], positions[j][0]],
                            [positions[i][1], positions[j][1]],
                            color=color, linewidth=0.6, alpha=0.6)
        else:
            # 链式连接（按列表顺序串联所有点）
            ax.plot(xs, ys, '-', color=color, linewidth=0.6, alpha=0.6)

        # 在每个元素位置画小圆点
        ax.scatter(xs, ys, color=color, s=8, alpha=0.8, zorder=5)

        drawn += 1

    # 添加图例（只显示前 20 种颜色中的一部分，避免图例过长）
    legend_elements = []
    for i in range(min(20, drawn)):
        legend_elements.append(
            Line2D([0], [0], color=colors[i % len(colors)],
                   linewidth=1.5, label=f'Net {i + 1}')
        )
    if drawn > 20:
        legend_elements.append(
            Line2D([0], [0], color='gray', linewidth=1.5,
                   label=f'... (共 {drawn} 个网表)')
        )
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right',
                  fontsize=6, framealpha=0.7)

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
                   show_labels=True, dpi=300, algo=0,
                   nets=None, block_dict=None, pin_dict=None,
                   max_nets_draw=None):
    """
    绘制矩形布局图，并可选择叠加网表连线。
    
    新增参数:
        nets: list of list of str，网表数据（来自 parse_nets_file）
        block_dict: {name: (x, y, w, h)} 模块位置字典
        pin_dict: {name: (x, y)} 引脚坐标字典
        max_nets_draw: 最多绘制的网表数
    """
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

    # ---- 新增：叠加网表连线 ----
    has_nets = (nets is not None and block_dict is not None
                and pin_dict is not None and len(nets) > 0)
    if has_nets:
        draw_nets_on_floorplan(ax, nets, block_dict, pin_dict, max_nets_draw)
    # ---------------------------

    ax.set_aspect('equal')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    title = f'Floorplan (algo{algo}, {len(blocks)} blocks)'
    if chip_width is not None:
        title += f' - Target W={chip_width} ({status})'
    if has_nets:
        n_shown = min(max_nets_draw, len(nets)) if max_nets_draw else len(nets)
        title += f' - Nets: {n_shown}'
    # ax.set_title(title)
    # ax.grid(True, linestyle='--', alpha=0.5)
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

def run_tune(args):
    """调优模式：按参数值读取 output/param_*/ 下的 floorplan + Btree 并绘图。"""
    script_dir = Path(__file__).resolve().parent
    tune_dir = Path(args.tune).resolve()
    if not tune_dir.is_dir():
        print(f"错误: 调优目录不存在: {tune_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir = tune_dir / "output"
    if not output_dir.is_dir():
        print(f"错误: 未找到调优输出目录: {output_dir}", file=sys.stderr)
        sys.exit(1)

    # 图片输出目录：默认 tune_dir/figures/，可用 --output 覆盖
    fig_root = Path(args.output).resolve() if getattr(args, 'output', None) else tune_dir / "figures"
    fig_root.mkdir(parents=True, exist_ok=True)

    # 从调优目录名提取 algo（如 HH-MM-SS_tune_a0_r_0.8-0.9）
    algo_match = re.search(r"_a(\d+)_", tune_dir.name)
    algo = int(algo_match.group(1)) if algo_match else args.algo

    # 每个参数值一个子目录
    param_dirs = sorted(d for d in output_dir.iterdir()
                        if d.is_dir() and d.name.startswith("param_"))
    if not param_dirs:
        print("错误: output/ 下没有 param_* 子目录（请先运行新结构的调优）", file=sys.stderr)
        sys.exit(1)

    total = 0
    for param_dir in param_dirs:
        pairs = get_sorted_file_pairs(param_dir, args.max_read)
        if not pairs:
            print(f"  警告: {param_dir.name} 中无 .floorplan + .Btree 文件对")
            continue

        # 由第一个 floorplan 推断块数
        _, blocks = parse_floorplan_file(str(pairs[0][0]))
        num_blocks = len(blocks) if blocks else args.blocks
        block_names = [f"sb{i}" for i in range(num_blocks)]

        out_sub = fig_root / param_dir.name
        out_sub.mkdir(parents=True, exist_ok=True)

        for fp_path, bt_path in pairs:
            stem = fp_path.stem
            print(f"\n  [{param_dir.name}] 处理 {stem}")
            chip_width, blocks = parse_floorplan_file(str(fp_path))
            if blocks:
                fp_img = out_sub / f"{stem}_floorplan.png"
                draw_floorplan(blocks, chip_width, output_image=str(fp_img),
                               show_labels=True, dpi=args.dpi, algo=algo)
            root_id, children = parse_btree_file(str(bt_path), num_blocks)
            if root_id >= 0:
                bt_img = out_sub / f"{stem}_btree.png"
                draw_btree(root_id, children, block_names,
                           output_image=str(bt_img), dpi=args.dpi)
            total += 1

    print(f"\n调优模式绘制完成，共 {total} 对文件，图片保存至: {fig_root}")

def run_batch(args):
    """批量处理主逻辑。"""
    script_dir = Path(__file__).resolve().parent
    
    if getattr(args, 'floorplan_dir', None):
        output_dir = Path(args.floorplan_dir).resolve()
    else:
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

    # 图片输出目录（支持 --output 覆盖；默认 results/floor_plan_figures/...）
    ratio_str = str(args.ratio).replace('.', '_')
    dir_name = f"test_{args.blocks}blocks_ratio_{ratio_str}_total_{args.num_runs}_algo{args.algo}"
    if getattr(args, 'output', None):
        fig_dir = Path(args.output).resolve()
    else:
        fig_dir = script_dir / "../results/floor_plan_figures" / dir_name
    fig_dir.mkdir(parents=True, exist_ok=True)

    # ---- 新增：如果启用了网表绘制，提前加载 .pl 和 .nets 文件 ----
    nets_data = None   # (nets, pin_dict)
    if args.draw_nets:
        testcase_dir = (script_dir / "../testcase").resolve()
        pl_path = testcase_dir / f"n{args.blocks}.pl"
        nets_path = testcase_dir / f"n{args.blocks}.nets"
        if pl_path.exists() and nets_path.exists():
            pin_dict = parse_pl_file(str(pl_path))
            nets = parse_nets_file(str(nets_path))
            nets_data = (nets, pin_dict)
            print(f"已加载网表数据: {len(nets)} 个网表, "
                  f"{len(pin_dict)} 个引脚 (来自 {pl_path.name}, {nets_path.name})")
        else:
            print(f"警告: 未找到测试用例文件 ({pl_path.name}, {nets_path.name})，"
                  f"跳过网表绘制")
    # ----------------------------------------------------------------

    # 预生成块名称列表（用于 B-tree 绘图）
    block_names = [f"sb{i}" for i in range(args.blocks)]

    for idx, (fp_path, bt_path) in enumerate(pairs, start=1):
        stem = fp_path.stem  # 如 "run1_2026-06-09_12:00:00"
        print(f"\n[{idx}/{len(pairs)}] 处理 {stem}")

        # --- 绘制 Floorplan ---
        chip_width, blocks = parse_floorplan_file(str(fp_path))
        if blocks:
            # ---- 修改：构建 block_dict 并传递 nets_data ----
            block_dict = _build_block_dict(blocks) if nets_data else None
            extra_kwargs = {}
            if nets_data:
                extra_kwargs['nets'] = nets_data[0]
                extra_kwargs['block_dict'] = block_dict
                extra_kwargs['pin_dict'] = nets_data[1]
                extra_kwargs['max_nets_draw'] = args.max_nets_draw
            # 生成带网表的图片（以 _with_nets 后缀区分）
            if nets_data:
                fp_img_nets = fig_dir / f"{stem}_floorplan_with_nets.png"
                draw_floorplan(blocks, chip_width, output_image=str(fp_img_nets),
                               show_labels=True, dpi=args.dpi, algo=args.algo,
                               **extra_kwargs)
            # 同时输出原始的 floorplan（不带网表）
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

def main(args=None):
    """绘制 floorplan / B*-tree 图。
    独立运行: python draw_fixed_outline.py --blocks 100 --ratio 0.1 ...
    作为模块: main(Namespace(...))  （由 test_scripts.py 调用）
    """
    if args is None:
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
        parser.add_argument("--floorplan_dir", type=str, default=None,
                            help="批量模式：显式指定 .floorplan/.Btree 所在目录（默认按 blocks/ratio/num_runs/algo 自动推导）")

        # --- 通用参数 ---
        parser.add_argument("-o", "--output", type=str, default=None,
                            help="单文件模式输出目录（默认与 .floorplan 同目录）")
        parser.add_argument("--dpi", type=int, default=300,
                            help="输出图片分辨率（默认300）")
        parser.add_argument("--no_labels", action="store_true",
                            help="不显示块名称标签")
        
        # --- 网表绘制参数 ---
        parser.add_argument("--draw_nets", action="store_true",
                            help="启用网表连线绘制（从 testcase/ 读取 .pl 和 .nets）")
        parser.add_argument("--max_nets_draw", type=int, default=None,
                            help="最多绘制的网表数量（默认全部），数值越大图越密集")
        
        parser.add_argument("--tune", type=str, default=None,
                            help="调优模式：传入调优运行目录（log/.../HH-MM-SS_tune_*），按参数值绘制 output/param_*/ 下的 floorplan/B*-tree")
        args = parser.parse_args()

    # ===== 调优模式 =====
    if getattr(args, 'tune', None):
        run_tune(args)
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

        # ---- 新增：单文件模式的网表加载 ----
        nets_data = None
        if args.draw_nets:
            testcase_dir = (fp_path.parent.parent / "testcase").resolve()
            if not testcase_dir.exists():
                # 尝试从脚本相对路径查找
                testcase_dir = (Path(__file__).resolve().parent / "../testcase").resolve()
            # 根据 blocks 数量推断 n 值
            n_val = num_blocks  # 用实际块数匹配
            # 尝试常见值
            for candidate in [100, 200, 300]:
                if abs(num_blocks - candidate) <= 10:  # 允许小误差
                    n_val = candidate
                    break
            pl_path = testcase_dir / f"n{n_val}.pl"
            nets_path = testcase_dir / f"n{n_val}.nets"
            if pl_path.exists() and nets_path.exists():
                pin_dict = parse_pl_file(str(pl_path))
                nets = parse_nets_file(str(nets_path))
                nets_data = (nets, pin_dict)
                print(f"已加载网表数据: {len(nets)} 个网表, {len(pin_dict)} 个引脚")
            else:
                print(f"警告: 未找到测试用例文件，跳过网表绘制")
        # -----------------------------------

        # 绘制 Floorplan
                # 确定输出目录
        if args.output:
            out_dir = Path(args.output)
        else:
            out_dir = fp_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        # 绘制 Floorplan
        fp_img = out_dir / f"{fp_path.stem}_floorplan.png"
        draw_floorplan(blocks, chip_width, output_image=str(fp_img),
                       show_labels=not args.no_labels, dpi=args.dpi)

        # 绘制 B-tree（如果有对应的 .Btree 文件）
        if args.btree:
            bt_path = Path(args.btree)
        else:
            bt_path = fp_path.with_suffix(".Btree")

        if bt_path.exists():
            root_id, children = parse_btree_file(str(bt_path), num_blocks)
            if root_id >= 0:
                bt_img = out_dir / f"{fp_path.stem}_btree.png"
                draw_btree(root_id, children, block_names,
                           output_image=str(bt_img), dpi=args.dpi)
        else:
            print("未找到对应的 .Btree 文件，跳过树图绘制")

        return

    # ===== 批量模式（同时提供了 --blocks 和 --ratio）=====
    if args.blocks is not None and args.ratio is not None:
        # num_runs 默认 1
        if args.num_runs is None:
            args.num_runs = 1
        run_batch(args)
        return

    # ===== 参数不足 =====
    print("错误: 请提供 --blocks 和 --ratio（批量模式），或 --floorplan（单文件模式）",
          file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()