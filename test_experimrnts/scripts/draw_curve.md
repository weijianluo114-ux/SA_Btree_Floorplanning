# 模拟退火曲线绘图脚本说明

## 概述

本脚本用于读取模拟退火过程中记录的 CSV 数据文件，并自动生成一系列曲线图，帮助分析算法收敛行为及温度参数的影响。

- **脚本位置**：`./scripts/draw_curve.py`
- **依赖**：Python 3.6+，`pandas`, `matplotlib`, `numpy`

## 主要功能

1. **自动定位最新 CSV**：扫描 `./results/curve_results/curve_data_Y-M-D_H:M:S` 目录，根据文件名中的时间戳选择最新生成的数据文件。
2. **绘制 7 个核心指标**（`width`, `height`, `area`, `wirelength`, `R`, `cost`, `T`）随 `Total_Moves` 的变化图：
   - 单独线性坐标图（每个指标一张图）
   - 组合子图（2×3 布局），所有指标使用对数纵轴，便于观察多量纲数据
3. **温度行为分析**：提取所有非零温度值，绘制前 5 个和后 5 个温度下的 `T_uphill`、`T_reject` 随 `T_Moves` 的变化曲线（每个温度一张图）。
4. **灵活输入输出**：
   - 可通过命令行指定 CSV 文件路径
   - 图片输出目录可自定义，默认 `./results/curve_figures/`
   - 所有输出图片文件名均包含原 CSV 文件名后缀（如 `width_curve_data_2026-06-04_12:48:28.png`）

## 安装依赖

```bash
pip install pandas matplotlib numpy
```

## 使用方法

### 1. 默认模式（自动读取最新 CSV）

```bash
cd ./scripts
python draw_curve.py
```

脚本会自动：

- 在 `../results/curve_results/` 目录下寻找所有 `curve_data_*.csv` 文件
- 根据文件名中的时间戳（如 `2026-06-04_12:48:28`）选择最新文件
- 将生成的图片保存到 `../results/curve_results/curve_data_Y-M-D_H:M:S`

### 2. 指定 CSV 文件

```bash
python draw_curve.py --csv /absolute/or/relative/path/to/your_data.csv
```

### 3. 指定图片输出目录

```bash
python draw_curve.py --output_dir ./my_figures
```

可同时使用 `--csv` 和 `--output-dir`。

## 命令行参数

| 参数             | 类型   | 默认值   | 说明                                                                        |
| ---------------- | ------ | -------- | --------------------------------------------------------------------------- |
| `--csv`        | 字符串 | `None` | CSV 文件路径。若不提供，则自动搜索 `./results/curve_results` 下最新文件。 |
| `--output_dir` | 字符串 | `None` | 图片输出目录。若不提供，默认使用 `./results/curve_figures`。              |

## 输入 CSV 格式要求

CSV 文件必须包含以下列（列名严格匹配）：

```
width,height,area,wirelength,R,cost,Total_Moves,T_Moves,T_uphill,T_reject,T
```

- **第一行**：列名（大小写敏感）
- **后续行**：每次采样点的数据（整数或浮点数）
- **典型内容示例**（来自 C++ 程序 `CSV:` 输出）：

```
width,height,area,wirelength,R,cost,Total_Moves,T_Moves,T_uphill,T_reject,T
283,2010,568830,764611,7.10247,43.6675,0,0,0,0,0
283,2010,568830,764593,7.10247,43.6675,1,1,0,0,85133
...
```

## 输出图片说明

所有图片保存为 PNG 格式，分辨率 150 DPI。

### 1. 单指标线性图（6 张）

- 文件名：`{metric}_{suffix}.png`例如：`width_curve_data_2026-06-04_12:48:28.png`
- 横轴：`Total_Moves`
- 纵轴：指标值（线性刻度）
- 图标题：`{metric} vs Total Moves`

### 2. 组合对数图（1 张）

- 文件名：`all_metrics_logy_{suffix}.png`
- 2 行 3 列子图，分别绘制 6 个指标
- 所有子图使用**对数纵轴**（`logy`），适合观察数量级差异大的指标（如面积 vs 线长）
- 横轴均为 `Total_Moves`

### 3. 温度行为图（最多 10 张）

- 提取所有非零温度值，排序后取：
  - 前 5 个最小温度
  - 后 5 个最大温度
- 每个温度一张图，文件名：`T_{temp_label}_uphill_reject_{suffix}.png`例如：`T_85133.00_uphill_reject_curve_data_2026-06-04_12:48:28.png`
- 横轴：`T_Moves`（该温度区间内累积的移动次数）
- 纵轴：`T_uphill`（上坡移动次数）、`T_reject`（拒绝次数）
- 图例自动区分两条曲线

## 注意事项

1. **中文字体支持**脚本中设置了 `SimHei` 等中文字体，若系统中没有相应字体，图标题中的中文可能显示为方框。这不影响图片保存，且本脚本生成的图片标题均为英文，通常无问题。若仍需显示中文，请安装相应字体或修改 `plt.rcParams`。
2. **温度值提取逻辑**

   - `T = 0` 被自动过滤（通常表示初始状态或无效数据）
   - 若非零温度总数不足 5 个，则后 5 个温度取所有剩余温度（即实际数量可能少于 5）
   - 温度值作为浮点数处理，文件名中的小数点点号会被替换为下划线（如 `85133.00` → `85133_00`），避免路径问题。
3. **CSV 文件命名约定**自动扫描功能依赖文件名格式：`curve_data_YYYY-MM-DD_HH:MM:SS.csv`。如果手动指定文件，则无此限制。
4. **性能与内存**对于 80 万行数据，`pandas` 可以轻松处理（约占用几十 MB 内存）。绘图操作可能稍慢（生成约 17 张图片），但仍在可接受范围内。
5. **横坐标说明**

   - `Total_Moves`：全局累积的扰动总次数（包括所有温度阶段）
   - `T_Moves`：当前温度阶段内的累积扰动次数（从进入该温度开始计数）
6. **错误处理**

   - 若 CSV 缺失必要列，脚本会抛出明确的 `ValueError`
   - 若没有非零温度数据，会跳过温度行为图的绘制并给出警告

## 示例工作流

```bash
# 1. 运行模拟退火并记录曲线
# root
python test_scripts.py --num_runs 10 --white_space_ratio 0.15 --record_curve

# 2. 生成曲线图
cd ./scripts
python draw_curve.py

# 3. 查看结果

```

## 扩展建议

- 如需调整图片大小、字体、颜色等，可修改脚本中的 `figsize`、`linewidth`、`dpi` 等参数。
- 若需要其他指标（如温度变化曲线、接受率等），可修改 C++ 输出格式并在本脚本中添加相应绘图函数。

---

**最后更新**：2026-06-04
**作者**：Simple
