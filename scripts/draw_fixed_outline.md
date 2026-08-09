# `draw_fixed_outline.py` 使用说明

这是一个用于 **可视化芯片布局规划结果** 的 Python 脚本。它支持：

- 绘制 **Floorplan 矩形布局图**（显示所有硬模块/软模块的位置和大小）
- 绘制对应的 **B\*-tree 二叉树结构图**（显示模块间的树形层次关系）
- **网表连线可视化**（可选）：从 `.pl` / `.nets` 文件中读取引脚和网表信息，在 Floorplan 上叠加绘制网表连线
- **两种运行模式**：批量模式（自动搜索输出目录）和单文件模式（指定具体文件）

---

## 1. 安装依赖

```bash
# 方式一：仅安装所需依赖
pip install matplotlib numpy

# 方式二：使用项目环境（推荐）
conda create SA_Btree python=3.11 -y
pip install -r requirements.txt
```

---

## 2. 两种运行模式

### 模式一：批量模式（Batch Mode）

根据实验参数自动定位输出目录，批量处理目录下所有 `.floorplan` + `.Btree` 文件对。

```bash
cd scripts
python draw_fixed_outline.py --blocks 100 --ratio 0.1 --num_runs 30 --algo 0 --max_read 5
```

**批量模式参数说明：**

| 参数                  | 类型  | 默认值   | 说明                                         |
| --------------------- | ----- | -------- | -------------------------------------------- |
| `--blocks`          | int   | 100      | 硬模块数量（如 100、200、300）               |
| `--ratio`           | float | 0.1      | 空白率（如 0.1、0.15）                       |
| `--num_runs`        | int   | 1        | 运行次数（即文件对数，如 30）                |
| `-a` / `--algo`   | int   | 0        | 算法模式：`0` = SA，`1` = GMS               |
| `--max_read`       | int   | 无限制   | 最多处理的文件对数（从第一个开始取）         |
| `--draw_nets`      | flag  | 关闭     | **启用网表连线绘制**（从 `testcase/` 读取 `.pl` 和 `.nets`） |
| `--max_nets_draw`  | int   | 全部     | 最多绘制的网表数量（数值越大图越密集）       |

**批量模式的目录自动定位规则：**

```
scripts/../output/test_{blocks}blocks_ratio_{ratio}_total_{num_runs}_algo{algo}/
```

例如 `--blocks 100 --ratio 0.1 --num_runs 30 --algo 0` 对应：

```
../output/test_100blocks_ratio_0_1_total_30_algo0/
```

**批量模式输出位置：**

图片自动保存在：

```
scripts/../results/floor_plan_figures/test_{blocks}blocks_ratio_{ratio}_total_{num_runs}_algo{algo}/
```

每个运行可能生成以下图片：

- `{run_name}_floorplan.png` — 矩形布局图（不含网表）
- `{run_name}_floorplan_with_nets.png` — 矩形布局图（叠加网表连线，仅在 `--draw_nets` 下生成）
- `{run_name}_btree.png` — B\*-tree 结构图

---

### 模式二：单文件模式（Single File Mode）

手动指定一个 `.floorplan` 文件（和可选的 `.Btree` 文件）进行绘制。

```bash
# 绘制 floorplan + 自动查找同名 .Btree 文件
python draw_fixed_outline.py --floorplan ../output/xxx/run1_2026-06-09_12:00:00.floorplan

# 手动指定 .Btree 文件
python draw_fixed_outline.py --floorplan ../output/xxx/run1.floorplan --btree ../output/xxx/run1.Btree
```

**单文件模式参数说明：**

| 参数              | 类型 | 默认值 | 说明                                                         |
| ----------------- | ---- | ------ | ------------------------------------------------------------ |
| `--floorplan`   | str  | 无     | `.floorplan` 文件路径（**必填**）                            |
| `--btree`       | str  | 无     | `.Btree` 文件路径（可选；未指定则自动查找同名 `.Btree`）     |
| `-o` / `--output` | str  | 无     | 图片输出目录（默认与 `.floorplan` 同目录）                   |
| `--draw_nets`   | flag | 关闭   | 启用网表连线绘制（自动从 `testcase/` 查找对应的 `.pl` / `.nets`） |

> **注意**：单文件模式下图片默认**保存到文件**（与 `.floorplan` 同目录，或 `--output` 指定目录），而非弹出窗口显示。

---

## 3. 通用参数

以下参数在两种模式下均可使用：

| 参数              | 类型 | 默认值 | 说明                                         |
| ----------------- | ---- | ------ | -------------------------------------------- |
| `--dpi`         | int  | 300    | 输出图片分辨率，值越大图片越清晰但文件也越大 |
| `--no_labels`   | flag | 关闭   | 指定后矩形块中央**不显示**块名称标签（仅单文件模式生效） |
| `--draw_nets`   | flag | 关闭   | 启用网表连线绘制                             |
| `--max_nets_draw` | int | 全部   | 最多绘制的网表数量                           |

> ⚠️ **注意**：当前批量模式下 `--no_labels` 不生效（`show_labels` 硬编码为 `True`），如需关闭标签请使用单文件模式。

---

## 4. 输入文件格式说明

### 4.1 `.floorplan` 文件格式

脚本会自动跳过文件中的元数据行，定位到数据行。支持以下头部（均可选）：

```
W:444                        # 可选：目标芯片宽度/高度（正方形约束）
Wirelength :235485           # 可选：线长信息（自动跳过）
Blocks:5                     # 可选：模块数量（自动跳过）
sb0 212 299 43 33 1          # 数据行：共6个字段
sb1 330 67 65 37 0
...
```

**数据行格式：** `名称 x y 参数3 参数4 方向`

| 字段      | 说明                                     |
| --------- | ---------------------------------------- |
| `名称`  | 模块名称，如 `sb0`, `sb1`, ...       |
| `x`     | 模块左下角的 x 坐标（整数）              |
| `y`     | 模块左下角的 y 坐标（整数）              |
| `参数3` | 见下方方向说明                           |
| `参数4` | 见下方方向说明                           |
| `方向`  | `0` 或 `1`，决定如何解析参数3和参数4 |

**方向字段解析规则：**

- **方向 `0`**：`参数3 = width`，`参数4 = height`
- **方向 `1`**：`参数3 = height`，`参数4 = width`

> **注意**：只有恰好包含 6 个字段的行才会被解析为数据行，其他行自动跳过。

### 4.2 `.Btree` 文件格式

B\*-tree 文件描述模块的二叉树结构关系：

```
Root: 4                      # 根节点 ID
0 1 2 3                      # 格式: 节点ID 父节点ID 左子节点ID 右子节点ID
1 4 -1 -1                    # -1 表示该子节点为空
2 0 -1 5
3 0 -1 -1
4 -1 0 1
5 2 -1 -1
...
```

| 字段         | 说明                                                     |
| ------------ | -------------------------------------------------------- |
| `Root: id` | 根节点的 ID                                              |
| 每行四个整数 | `节点ID 父节点ID 左子节点ID 右子节点ID`，`-1` 表示空 |

### 4.3 `.pl` 文件格式（新增）

引用库的引脚坐标文件，用于网表连线绘制。每行格式：

```
p1 0 444                      # 引脚名称 x y
p2 111 444
...
```

### 4.4 `.nets` 文件格式（新增）

网表文件，描述各模块/引脚之间的连接关系：

```
NumNets : 10                  # 网表总数
NumPins : 30                  # 引脚总数
NetDegree : 4                 # 当前网表的度数（包含元素数）
sb0                           # 该网表中的元素（模块名或引脚名）
p1
p2
sb1
NetDegree : 3
...
```

---

## 5. 输出示例

### Floorplan 矩形布局图

- 每个模块绘制为带边框的矩形，半透明浅蓝色填充
- 矩形中央标注模块名称（可通过 `--no_labels` 关闭，仅单文件模式）
- 红色/绿色虚线标注目标芯片尺寸：
  - **绿色虚线** = 所有模块在目标尺寸内（满足约束）
  - **红色虚线** = 有模块超出目标尺寸（超出约束）
- 坐标轴等比例显示，**已隐藏上框线和右框线**
- **无网格线、无标题**（更简洁）
- **可选**：叠加网表连线（`--draw_nets`）：
  - 每个网表使用 tab20 色表中的不同颜色
  - 小度数网表（≤4）使用**完全连接**（两两连线）
  - 大度数网表（>4）使用**链式连接**（按列表顺序串联）
  - 每个元素位置绘制小圆点
  - 右上角显示网表图例（最多显示 20 个网表）

### B\*-tree 二叉树结构图

- 根节点位于最上方，子节点向下展开
- 左子节点在左，右子节点在右（由中序遍历定位）
- 节点为浅蓝色圆形黑色边框，标注模块名称
- **紧凑布局**：画布尺寸根据树的宽度和深度动态计算（`fig_w = max(5, 宽度×0.19)`，`fig_h = max(5, 深度×1.3)`）
- 标题显示根节点 ID 和总节点数

---

## 6. 完整用法示例

### 批量处理一批实验结果

```bash
cd scripts

# 处理 n100, ratio=0.1, 30次运行, SA算法, 只取前5对文件
python draw_fixed_outline.py --blocks 100 --ratio 0.1 --num_runs 30 --algo 0 --max_read 5

# 处理 n200, ratio=0.15, 50次运行, GMS算法
python draw_fixed_outline.py --blocks 200 --ratio 0.15 --num_runs 50 --algo 1

# 处理 n300, 同时绘制网表连线, 限制最多20个网表
python draw_fixed_outline.py --blocks 300 --ratio 0.1 --num_runs 20 --algo 0 --draw_nets --max_nets_draw 20

# 不带标签, 提高分辨率（注意：--no_labels 在批量模式下当前不生效）
python draw_fixed_outline.py --blocks 300 --ratio 0.1 --num_runs 20 --algo 0 --no_labels --dpi 600
```

### 单文件预览

```bash
cd scripts

# 绘制 floorplan + 自动查找同名的 .Btree 文件
python draw_fixed_outline.py --floorplan ../output/test_100blocks_ratio_0_1_total_30_algo0/run1_2026-06-09_12:00:00.floorplan

# 指定 btree 文件, 保存到指定目录
python draw_fixed_outline.py --floorplan ../output/xxx/run1.floorplan --btree ../output/xxx/run1.Btree -o ./my_figures

# 启用网表连线
python draw_fixed_outline.py --floorplan ../output/xxx/run1.floorplan --draw_nets --max_nets_draw 30
```

---

## 7. 可视化定制

如果需要调整图形的外观，可以修改脚本中的以下参数：

| 效果                    | 脚本中对应的参数                                              | 位置（函数）           |
| ----------------------- | ------------------------------------------------------------- | ---------------------- |
| 矩形填充色              | `facecolor='lightblue'`                                     | `draw_floorplan()`   |
| 矩形透明度              | `alpha=0.7`                                                 | `draw_floorplan()`   |
| 矩形边框宽度            | `linewidth=1.5`                                             | `draw_floorplan()`   |
| 标签字体大小            | `fontsize=8`                                                | `draw_floorplan()`   |
| 节点颜色                | `color='lightblue'`                                         | `draw_btree()`       |
| 节点大小                | `markersize=20`                                             | `draw_btree()`       |
| 树中标签字体大小        | `fontsize=6`                                                | `draw_btree()`       |
| 图片尺寸（floorplan）   | `figsize=(12, 10)`                                          | `draw_floorplan()`   |
| 树图尺寸                | `fig_w = max(5, tree_width * 0.19)` / `fig_h = max(5, tree_depth * 1.3)` | `draw_btree()` |
| 网表连线颜色            | `cm.tab20` 色表循环                                          | `draw_nets_on_floorplan()` |
| 网表连线宽度/透明度     | `linewidth=0.6, alpha=0.6`                                  | `draw_nets_on_floorplan()` |

---

## 8. 常见问题

**Q: 提示 `没有可绘制的块`？**
A: 检查 `.floorplan` 文件格式是否正确，确保数据行包含 6 个字段。

**Q: 批量模式提示 `输出目录不存在`？**
A: 确认 `--blocks`、`--ratio`、`--num_runs`、`--algo` 组合与输出目录名称匹配，目录位于 `scripts/../output/` 下。

**Q: 提示 `无对应的 .Btree 文件`？**
A: 批量模式下，脚本会自动查找同名 `.Btree` 文件。如果某些运行没有对应的树文件，这些运行会被跳过（仅跳过树图，不影响 floorplan 绘制）。

**Q: `--no_labels` 在批量模式下无效？**
A: 当前批量模式中 `show_labels` 参数硬编码为 `True`，`--no_labels` 仅单文件模式生效。如需批量关闭标签，可修改脚本中 `run_batch()` 的 `show_labels=True` 为 `show_labels=not args.no_labels`。

**Q: 网表连线在哪里读取？**
A: 脚本从 `testcase/` 目录自动读取对应的 `n{blocks}.pl` 和 `n{blocks}.nets` 文件。例如 `--blocks 100` 会读取 `testcase/n100.pl` 和 `testcase/n100.nets`。

**Q: 网表图颜色太多看不清怎么办？**
A: 使用 `--max_nets_draw 20` 限制绘制的网表数量。默认最多显示 20 种不同颜色的图例。

**Q: 单文件模式下图片没有弹出窗口？**
A: 当前版本单文件模式默认**保存到文件**（与 `.floorplan` 同目录），而不是弹出显示。如需弹出窗口预览，需手动修改代码将 `output_image` 参数设为 `None`。

---

## 与旧版文档的主要差异

旧版文档存在以下过时/不准确之处，新版已全部修正：

| 旧版                                                         | 新版                                                          |
| ------------------------------------------------------------ | ------------------------------------------------------------- |
| 仅描述矩形图绘制                                             | 新增 B\*-tree 图绘制、网表连线绘制的完整说明                  |
| 只有单文件使用方式                                           | 新增批量模式的完整说明                                        |
| 缺少 `.Btree` 文件格式说明                                   | 补充了 `.Btree` 文件格式的解析规则                            |
| 单文件模式描述为"弹出窗口显示（不保存到文件）"               | 单文件模式默认保存到文件，可通过 `-o` 指定输出目录           |
| 使用过时的运行命令                                           | 更新为当前脚本支持的所有参数和用法                            |
| —                                                            | 新增 `--draw_nets` / `--max_nets_draw` / `--output` 参数说明 |
| —                                                            | 新增 `.pl` 和 `.nets` 文件格式说明                            |
| —                                                            | 新增网表叠加绘制的可视化定制说明                              |
| —                                                            | 新增 `--no_labels` 在批量模式下不生效的说明                   |
| Floorplan 图有网格和标题                                     | 当前版本已去除网格和标题，隐藏上/右框线                       |
| B-tree 图固定画布尺寸                                        | 当前版本根据树的宽度/深度动态计算紧凑画布尺寸                 |


---

## 主要变更总结

| 项目 | 旧版 (MD) | 新版 (代码实际行为) |
|------|-----------|-------------------|
| **网表可视化** | 不存在 | 新增 `--draw_nets` / `--max_nets_draw`，叠加彩色连线 |
| **文件格式说明** | 仅 `.floorplan` + `.Btree` | 新增 `.pl` / `.nets` 格式说明 |
| **单文件模式** | "弹出窗口显示" | **默认保存到文件**，可用 `-o` 指定目录 |
| **新增参数** | — | `--draw_nets`, `--max_nets_draw`, `--output` / `-o` |
| **Floorplan 外观** | 有网格线 + 标题 | **无网格、无标题**，隐藏上/右框线 |
| **B-tree 画布** | 固定尺寸 | **动态紧凑布局**（根据树宽/深计算） |
| **批量模式 --no_labels** | 描述为通用参数 | **实际不生效**（硬编码为 True），已标注 |
| **输出文件** | 每 run 2 张图 | 启用 `--draw_nets` 时额外生成 `*_with_nets.png` |