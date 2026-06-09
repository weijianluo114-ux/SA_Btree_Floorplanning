# `draw_fixed_outline.py` 使用说明

这是一个用于 **可视化芯片布局规划结果** 的 Python 脚本。它支持：

- 绘制 **Floorplan 矩形布局图**（显示所有硬模块/软模块的位置和大小）
- 绘制对应的 **B\*-tree 二叉树结构图**（显示模块间的树形层次关系）
- **两种运行模式**：批量模式（自动搜索输出目录）和单文件模式（指定具体文件）

---

## 1. 安装依赖

```bash
# 方式一：仅安装所需依赖
pip install matplotlib

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

**参数说明：**

| 参数                | 类型  | 默认值 | 说明                                 |
| ------------------- | ----- | ------ | ------------------------------------ |
| `--blocks`        | int   | 100    | 硬模块数量（如 100、200、300）       |
| `--ratio`         | float | 0.1    | 空白率（如 0.1、0.15）               |
| `--num_runs`      | int   | 1      | 运行次数（即文件对数，如 30）        |
| `-a` / `--algo` | int   | 0      | 算法模式：`0` = SA，`1` = GMS    |
| `--max_read`      | int   | 无限制 | 最多处理的文件对数（从第一个开始取） |

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

每个运行会生成两张图片：

- `{run_name}_floorplan.png` — 矩形布局图
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

**参数说明：**

| 参数            | 类型 | 默认值 | 说明                                                         |
| --------------- | ---- | ------ | ------------------------------------------------------------ |
| `--floorplan` | str  | 无     | 单文件模式：`.floorplan` 文件路径（**必填**）        |
| `--btree`     | str  | 无     | `.Btree` 文件路径（可选；未指定则自动查找同名 `.Btree`） |

> **注意**：单文件模式下图片默认弹出窗口显示（不保存到文件），适合快速预览。

---

## 3. 通用参数

以下参数在两种模式下均可使用：

| 参数            | 类型 | 默认值 | 说明                                         |
| --------------- | ---- | ------ | -------------------------------------------- |
| `--dpi`       | int  | 300    | 输出图片分辨率，值越大图片越清晰但文件也越大 |
| `--no_labels` | flag | 关闭   | 指定后矩形块中央**不显示**块名称标签   |

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

---

## 5. 输出示例

### Floorplan 矩形布局图

- 每个模块绘制为带边框的矩形，半透明浅蓝色填充
- 矩形中央标注模块名称（可通过 `--no_labels` 关闭）
- 红色/绿色虚线标注目标芯片尺寸：
  - **绿色虚线** = 所有模块在目标尺寸内（满足约束）
  - **红色虚线** = 有模块超出目标尺寸（超出约束）
- 坐标轴等比例显示，带网格线

### B\*-tree 二叉树结构图

- 根节点位于最上方，子节点向下展开
- 左子节点在左，右子节点在右（由中序遍历定位）
- 节点为浅蓝色圆形，标注模块名称
- 树形紧凑布局，自动适配画布大小

---

## 6. 完整用法示例

### 批量处理一批实验结果

```bash
cd scripts

# 处理 n100, ratio=0.1, 30次运行, SA算法, 只取前5对文件
python draw_fixed_outline.py --blocks 100 --ratio 0.1 --num_runs 30 --algo 0 --max_read 5

# 处理 n200, ratio=0.15, 50次运行, GMS算法
python draw_fixed_outline.py --blocks 200 --ratio 0.15 --num_runs 50 --algo 1

# 处理 n300, ratio=0.1, 全部文件, 不显示标签, 提高分辨率
python draw_fixed_outline.py --blocks 300 --ratio 0.1 --num_runs 20 --algo 0 --no_labels --dpi 600
```

### 单文件预览

```bash
cd scripts

# 仅查看 floorplan（自动查找同目录下的 .Btree 文件）
python draw_fixed_outline.py --floorplan ../output/test_100blocks_ratio_0_1_total_30_algo0/run1_2026-06-09_12:00:00.floorplan

# 指定 btree 文件
python draw_fixed_outline.py --floorplan ../output/xxx/run1.floorplan --btree ../output/xxx/run1.Btree
```

---

## 7. 可视化定制

如果需要调整图形的外观，可以修改脚本中的以下参数：

| 效果                  | 脚本中对应的参数          | 位置（函数）         |
| --------------------- | ------------------------- | -------------------- |
| 矩形填充色            | `facecolor='lightblue'` | `draw_floorplan()` |
| 矩形透明度            | `alpha=0.7`             | `draw_floorplan()` |
| 矩形边框宽度          | `linewidth=1.5`         | `draw_floorplan()` |
| 标签字体大小          | `fontsize=8`            | `draw_floorplan()` |
| 节点颜色              | `color='lightblue'`     | `draw_btree()`     |
| 节点大小              | `markersize=20`         | `draw_btree()`     |
| 树中标签字体大小      | `fontsize=6`            | `draw_btree()`     |
| 图片尺寸（floorplan） | `figsize=(12, 10)`      | `draw_floorplan()` |

---

## 8. 常见问题

**Q: 提示 `没有可绘制的块`？**
A: 检查 `.floorplan` 文件格式是否正确，确保数据行包含 6 个字段。

**Q: 批量模式提示 `输出目录不存在`？**
A: 确认 `--blocks`、`--ratio`、`--num_runs`、`--algo` 组合与输出目录名称匹配，目录位于 `scripts/../output/` 下。

**Q: 提示 `无对应的 .Btree 文件`？**
A: 批量模式下，脚本会自动查找同名 `.Btree` 文件。如果某些运行没有对应的树文件，这些运行会被跳过（仅跳过树图，不影响 floorplan 绘制）。

**Q: 单文件模式下图片没有保存？**
A: 单文件模式默认弹出窗口显示。如需保存，请使用批量模式或修改脚本将 `output_image=None` 改为文件路径。

---

## 与旧版文档的主要差异

旧版文档存在以下过时/不准确之处，新版已全部修正：

| 旧版                                 | 新版                                                    |
| ------------------------------------ | ------------------------------------------------------- |
| 引用 `--input_file` 参数（不存在） | 改用 `--floorplan` 参数                               |
| 引用 `-o` 输出参数（不存在）       | 批量模式自动保存到 `results/floor_plan_figures/` 目录 |
| 仅描述矩形图绘制                     | 新增 B\*-tree 图绘制的完整说明                          |
| 只有单文件使用方式                   | 新增批量模式的完整说明                                  |
| 缺少 `.Btree` 文件格式说明         | 补充了 `.Btree` 文件格式的解析规则                    |
| 使用过时的运行命令                   | 更新为当前脚本支持的所有参数和用法                      |
