# 模拟退火曲线绘图脚本说明

## 概述

本脚本用于读取模拟退火过程中记录的 CSV 数据文件，并自动生成一系列曲线图，帮助分析算法收敛行为、温度参数的影响以及不同参数的对比。

- **脚本位置**：`./scripts/draw_curve.py`
- **依赖**：Python 3.6+，`pandas`, `matplotlib`, `numpy`

## 主要功能

1. **自动定位最新数据**：扫描 `./results/curve_results/` 下所有 `curve_data_*` 子文件夹，根据文件夹名中的时间戳选择最新生成的数据目录。
2. **热力图风格曲线绘制**：6 个核心指标（`width`, `height`, `area`, `wirelength`, `R`, `cost`）随 `Total_Moves` 的变化图，**线段颜色根据温度的对数值（log10(T)）映射**（类热力图），直观展示不同温度阶段的搜索行为。
   - 单独线性坐标图（每个指标一张图）
   - 组合子图（2×3 布局），所有子图使用对数纵轴，便于观察多量纲数据
3. **温度自身曲线**：绘制 `T` 随 `Total_Moves` 的变化图（对数纵轴），同样使用热力图着色。
4. **前/后 N 行数据绘图**（`--n_top` / `--n_back`）：可额外绘制数据集的**前 N 行**或**后 N 行**曲线，用于观察初始收敛或最终收敛阶段的细节。
5. **拒绝率分析图**（`--rejection-rate`）：读取多个 `curve_data_run*.csv` 文件，将各 run 的拒绝率（`T_reject / T_Moves`）随温度变化的散点图绘制在同一张图上，不同 run 用不同颜色区分。
6. **参数调优模式**（`--tune`）：读取 `tune_*` 文件夹下所有 `param_*/curve_data.csv`，为每组参数独立绘图，便于对比不同参数设置的效果。
7. **灵活输入输出**：
   - 可通过命令行指定 CSV 文件路径或目录
   - 图片输出目录可自定义
   - 支持处理单文件或批量处理 `curve_data_run*.csv`
   - 每个 run 的图片放在独立子文件夹中（如 `run1/`, `run2/`）

## 安装依赖

```bash
pip install pandas matplotlib numpy
```

## 使用方法

### 1. 默认模式（自动读取最新数据）

```bash
cd ./scripts
python draw_curve.py
```

脚本会自动：

- 在 `../results/curve_results/` 目录下寻找所有 `curve_data_*` 子文件夹
- 根据文件夹名中的时间戳（如 `2026-06-04_12:48:28`）选择最新的文件夹
- 处理该文件夹下所有 `curve_data_run*.csv` 文件
- 将生成的图片保存到 `../results/curve_figures/<最新文件夹名>/runX/`

### 2. 指定 CSV 文件或目录

```bash
# 指定单个文件
python draw_curve.py --csv /path/to/curve_data_run1.csv

# 指定目录（处理其中所有 curve_data_run*.csv）
python draw_curve.py --csv /path/to/curve_data_folder/
```

### 3. 指定图片输出目录

```bash
python draw_curve.py --output_dir ./my_figures
```

可同时使用 `--csv` 和 `--output_dir`。

### 4. 绘制前/后 N 行细节曲线

```bash
# 额外绘制前 500 个数据点的曲线
python draw_curve.py --n_top 500

# 额外绘制后 1000 个数据点的曲线
python draw_curve.py --n_back 1000

# 同时绘制
python draw_curve.py --n_top 500 --n_back 1000
```

### 5. 绘制拒绝率散点图

```bash
# 自动选择最新文件夹中的 CSV 文件
python draw_curve.py --rejection-rate

# 指定目录
python draw_curve.py --rejection-rate /path/to/curve_data_folder/

# 指定取前 N 个最高温度（默认 60）
python draw_curve.py --rejection-rate --rr-n-top 100
```

### 6. 参数调优模式

```bash
# 自动选择最新的 tune_* 文件夹
python draw_curve.py --tune

# 指定调优目录
python draw_curve.py --tune /path/to/tune_algo0_2026-06-06_20:48:33/
```

## 命令行参数

| 参数                 | 类型   | 默认值    | 说明                                                                                     |
| -------------------- | ------ | --------- | ---------------------------------------------------------------------------------------- |
| `--csv`            | 字符串 | `None`  | CSV 文件路径或包含 `curve_data_run*.csv` 的目录。若不提供，则自动搜索最新时间戳文件夹。 |
| `--output_dir`     | 字符串 | `None`  | 图片输出根目录。若不提供，默认使用 `./results/curve_figures/<文件夹名>/`。             |
| `--sample_step`    | 整数   | `100`   | 绘图时每多少点采样一次（默认 100）。值越小曲线越精细，但绘图越慢。                      |
| `--n_top`          | 整数   | `0`     | 额外绘制前 N 个数据点的曲线图（使用 sample_step=1 避免欠采样）。                      |
| `--n_back`         | 整数   | `0`     | 额外绘制后 N 个数据点的曲线图（使用 sample_step=1 避免欠采样）。                      |
| `--rejection-rate` | 可选   | `None`  | 绘制拒绝率散点图。可指定目录路径，或留空自动选择最新文件夹。                            |
| `--rr-n-top`       | 整数   | `60`    | 与 `--rejection-rate` 配合使用，取前 N 个最高温度绘制。                                 |
| `--tune`           | 可选   | `None`  | 调优模式。可指定 `tune_*` 目录路径，或留空自动选择最新。                              |

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

所有图片保存为 PNG 格式，分辨率 **400 DPI**。

### 1. 单指标热力图（6 张 + 1 张温度图）

- 文件名：`{metric}_heatmap_{suffix}.png`
  - 例如：`width_heatmap_curve_data_run1.png`
  - 温度图：`T_heatmap_curve_data_run1.png`
- 横轴：`Total_Moves`
- 纵轴：指标值（线性刻度，温度图使用对数刻度）
- 线段颜色：根据温度的对数值 `log10(T)` 映射（`jet` 色图），颜色越红表示温度越高
- 右侧 colorbar：显示对应的真实温度值

### 2. 组合热力图（1 张）

- 文件名：`all_metrics_heatmap_{suffix}.png`
- 2 行 3 列子图，分别绘制 6 个指标
- 所有子图使用**对数纵轴**（`logy`），适合观察数量级差异大的指标
- 所有子图使用统一的温度颜色映射，右侧共享 colorbar
- 横轴均为 `Total_Moves`

### 3. 前/后 N 行细节图（可选，各 7 张）

- 文件名：`{metric}_heatmap_{suffix}_first{N}.png` 或 `_last{N}.png`
- 使用 `sample_step=1`，不降采样
- 包含单指标图和组合图

### 4. 拒绝率散点图（可选，1 张）

- 文件名：`rejection_rates_top{N}_algo{algo}.png`
- 横轴：温度（对数刻度）
- 纵轴：拒绝率 `T_reject / T_Moves`（范围 0~1）
- 每个 run 用不同颜色散点表示，图例标注 `runX`

### 5. 温度行为图

> ⚠️ **当前版本中 `plot_temperature_behaviors` 函数已存在但默认注释掉了调用**，如需启用可取消 `process_single_csv` 中相关行的注释。

## 注意事项

1. **中文字体支持**：脚本中设置了 `SimHei` 等中文字体，若系统中没有相应字体，图标题中的中文可能显示为方框。当前脚本生成的图片标题均为英文，通常无问题。
2. **温度过滤逻辑**：
   - `T = 0` 的行在热力图中被自动过滤（通常表示初始状态或无效数据），因为无法计算 `log10(0)`
   - 颜色映射范围基于非零温度的最小值和最大值
3. **CSV 文件命名约定**：自动扫描功能依赖子文件夹名带时间戳格式 `curve_data_YYYY-MM-DD_HH:MM:SS`（或带 algo 前缀如 `curve_data_algo0_2026-06-06_20:48:33_algo0`），以及文件名 `curve_data_run*.csv` 的命名模式。
4. **性能与内存**：对于 80 万行数据，`pandas` 可轻松处理。采样步长 `sample_step` 控制绘图密度，默认 100 可在画质和速度间取得平衡。`LineCollection` 方式绘图比普通 `plot` 稍慢，但能呈现温度信息。
5. **横坐标说明**：
   - `Total_Moves`：全局累积的扰动总次数（包括所有温度阶段）
   - `T_Moves`：当前温度阶段内的累积扰动次数（从进入该温度开始计数）
6. **错误处理**：
   - 若 CSV 缺失必要列，脚本会抛出明确的 `ValueError`
   - 若没有非零温度数据，热力图会跳过并给出警告
   - 若目录中无符合条件的 CSV 文件，脚本会抛出 `FileNotFoundError`

## 示例工作流

```bash
# 1. 运行模拟退火并记录曲线
# 在项目根目录
python test_scripts.py --num_runs 10 --white_space_ratio 0.15 --record_curve

# 2. 生成曲线热力图
cd ./scripts
python draw_curve.py

# 3. 只看前 500 步和后 1000 步的细节
python draw_curve.py --n_top 500 --n_back 1000

# 4. 绘制拒绝率对比图
python draw_curve.py --rejection-rate

# 5. 查看参数调优结果
python draw_curve.py --tune

# 6. 查看结果
ls ../results/curve_figures/
```

## 扩展建议

- 如需调整图片大小、字体、颜色等，可修改脚本中的 `figsize`、`linewidth`、`DPI` 等参数。
- 色图默认为 `jet`，可修改 `cmap='jet'` 为其他 Matplotlib 色图（如 `'plasma'`, `'viridis'`）。
- 若需要温度行为曲线（`T_uphill`/`T_reject` 随 `T_Moves` 变化），取消 `process_single_csv` 中的 `plot_temperature_behaviors` 调用注释即可。

---

**最后更新**：2026-06-20
**作者**：Simple

---

## 主要变更总结

| 项目 | 旧版 (MD) | 新版 (代码实际行为) |
|------|-----------|-------------------|
| **绘图风格** | 普通折线图 | **热力图风格** — 线段颜色按 `log10(T)` 映射 |
| **温度行为图** | 默认启用（前后各5个温度） | **默认禁用**（代码中已注释），函数保留但需手动启用 |
| **新增功能** | — | `--n_top`/`--n_back` 前/后N行细节绘制 |
| **新增功能** | — | `--rejection-rate` 拒绝率散点图 |
| **新增功能** | — | `--tune` 参数调优模式 |
| **输出分辨率** | 150 DPI | **400 DPI** |
| **文件名格式** | `{metric}_{suffix}.png` | `{metric}_heatmap_{suffix}.png` |
| **自动定位** | 扫描最新 CSV 文件 | 扫描最新**子文件夹**，再找其中 `curve_data_run*.csv` |
| **CSV 参数** | 仅接受文件路径 | **文件或目录**均可 |
| **输出目录结构** | 所有图片在同一个目录 | 每个 run 放入独立子文件夹 `runX/` |