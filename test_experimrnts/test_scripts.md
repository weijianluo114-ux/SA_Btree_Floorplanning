# test_scripts.py — 批量实验与参数调优脚本

> 本脚本替代了原始的 Bash 批处理方案，提供**批量实验**、**曲线记录**、**参数调优**三大核心功能，并自动完成结果提取、统计分析和日志归档。

---

## 目录

- [快速开始](#快速开始)
- [命令行参数一览](#命令行参数一览)
- [算法模式对照表](#算法模式对照表)
- [批量实验模式](#1-批量实验模式)
- [曲线记录模式](#2-曲线记录模式)
- [参数调优模式](#3-参数调优模式)
- [常用示例](#常用示例)
- [输出文件结构](#输出文件结构)
- [注意事项](#注意事项)

---

## 快速开始

```bash
# 进入脚本目录
cd test_experimrnts

# 最简单的用法：2 次实验，空白比 0.15
python test_scripts.py --num_runs 2 --white_space_ratio 0.15
```

脚本会自动：
1. 执行 `make -f Makefile.debug` 编译 C++ 程序
2. 生成随机种子并保存到 `./seeds/`
3. 运行指定次数，记录每次的原始输出
4. 提取 `Width`、`Height`、`Area`、`Wirelength`、`R`、`Cost` 等指标
5. 计算平均值、标准差、五数汇总（剔除 IQR 异常值）
6. 输出统计表格到终端并保存到日志文件

---

## 命令行参数一览

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--executable` | str | `./bin/hw3_dbg` | 可执行文件路径（相对于脚本目录） |
| `--hardblocks` | str | `./testcase/n100.hardblocks` | hardblocks 文件路径 |
| `--nets` | str | `./testcase/n100.nets` | nets 文件路径 |
| `--terminals` | str | `./testcase/n100.pl` | terminals 文件路径 |
| `--white_space_ratio` | float | `0.1` | 空白比例 |
| `--num_runs` | int | `20` | 运行次数 |
| `--output_dir` | str | `None` | floorplan 输出目录（自动生成） |
| `--log_file` | str | `None` | 完整日志文件路径（自动生成） |
| `--seed_file` | str | `None` | 种子文件路径（指定后可复现实验） |
| `--skip_make` | flag | `False` | 跳过 make 编译步骤 |
| `--record_curve` | flag | `False` | 记录模拟退火过程中的详细参数曲线 |
| `-a` / `--algo` | int | `0` | 算法模式（见下表） |
| `--tune` | str | `None` | 调优配置文件（YAML），触发参数调优模式 |

---

## 算法模式对照表

| `-a` 值 | 算法名称 | JSON 配置块名 | 说明 |
|---------|----------|---------------|------|
| `0` | **SA** | `"SA"` | 原始模拟退火算法 |
| `1` | **GMS** | `"GMS"` | Guided Move Selection + SA |
| `2` | **FastSA** | `"FastSA"` | 快速模拟退火（动态温度调度） |
| `3` | **GMS_FastSA** | `"GMS_FastSA"` | GMS 偏置选择 + FastSA 温度调度 |
| `4` | **SawTooth_FastSA** | `"SawTooth_FastSA"` | 锯齿形回火 FastSA |
| `5` | **GMS_DoubleMatrix** | `"GMS_DoubleMatrix"` | 双矩阵 GMS（Swap/Move 分离） |

---

## 1. 批量实验模式

这是默认模式。脚本会运行 `--num_runs` 次实验，生成独立种子，汇总统计结果。

```bash
# 基本批量实验（20 次，空白比 0.1）
python test_scripts.py --num_runs 20 --white_space_ratio 0.1

# 指定不同的测试数据集（n200，空白比 0.15）
python test_scripts.py \
    --hardblocks ./testcase/n200.hardblocks \
    --nets ./testcase/n200.nets \
    --terminals ./testcase/n200.pl \
    --white_space_ratio 0.15 \
    --num_runs 30
```

**输出示例（终端统计表格）：**

```
========== 统计结果 ==========
指标        平均值         标准差         最小值     Q1           中位数     Q3           最大值
---------------------------------------------------------------------------------------------------------
Width       2560.0000      15.0000       2530.0000 2545.0000     2560.0000 2570.0000     2590.0000
Height      2410.0000      12.0000       2390.0000 2400.0000     2415.0000 2420.0000     2440.0000
Cost        2.4567         0.1234        2.3456    2.4000        2.4567    2.5000        2.6000
算法模式：0
可行解统计: found = 18, not found = 2
```

---

## 2. 曲线记录模式

记录模拟退火**每一次扰动**的代价、温度等详细数据，用于绘制收敛曲线。

> **约束**：曲线模式下 `--num_runs` 最多为 10（防止数据量过大）。
> 曲线数据保存在 `./results/curve_results/` 目录下，每行 CSV 格式：`width,height,area,wirelength,R,cost,Total_Moves,T_Moves,T_uphill,T_reject,T`

```bash
# 曲线记录实验（5 次）
python test_scripts.py --num_runs 5 --white_space_ratio 0.1 --record_curve

# 曲线记录 + 指定算法
python test_scripts.py --num_runs 5 --white_space_ratio 0.1 --record_curve -a 1
```

曲线 CSV 文件可用于后续绘图：

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("results/curve_results/curve_data_algo0_.../curve_data_run1_algo0.csv")
plt.plot(df["Total_Moves"], df["cost"])
plt.xlabel("Iteration")
plt.ylabel("Cost")
plt.show()
```

---

## 3. 参数调优模式

对某个算法参数进行**网格搜索**，自动对比不同参数值下的平均 Cost 和可行解率。

> **前置条件**：需安装 PyYAML：`pip install pyyaml`

### 3.1 准备调优配置文件（YAML）

创建 `tune_config.yaml`：

```yaml
algo: 0                # 算法模式（0=SA）
parameter: "r"         # 要调优的参数名（对应 JSON 配置块中的键）
start: 0.5             # 起始值
end: 0.95              # 结束值
step: 0.05             # 步长
num_runs: 5            # 每个参数值运行次数（不同种子）
fixed:                 # 固定参数（可选，覆盖结构体默认值）
  k: 40
  time_limit: 1195
```

### 3.2 运行调优

```bash
# 基本调优
python test_scripts.py --tune tune_config.yaml --white_space_ratio 0.1

# 调优 + 曲线记录（强制 num_runs=1，最多 10 个参数值）
python test_scripts.py --tune tune_config.yaml --white_space_ratio 0.1 --record_curve
```

### 3.3 输出目录结构

```
./log/tune_algo0_r_2026-06-08_16:21:22/       # 调优根日志目录
    param_r0_5/                                # 每个参数值一个文件夹
        running_results_algo0_r0_5.txt         # 原始输出 + 完整统计
    param_r0_55/
        running_results_algo0_r0_55.txt
    summary.txt                                # 整体汇总表格

./config/                                      # 自动生成的 JSON 配置文件
    tune_algo0_r0_5.json
    tune_algo0_r0_55.json
```

### 3.4 调优汇总输出示例

```
======================================================================
调优汇总 (SA.r)
======================================================================
参数值       平均Cost      可行解率
--------------------------------------------------
0.500000     3.2456        40.0%
0.550000     2.9876        60.0%
0.600000     2.6543        80.0%
0.650000     2.5432        100.0%
0.700000     2.4876        100.0%
0.750000     2.4567        100.0%
0.800000     2.4890        100.0%
0.850000     2.5234        100.0%
0.900000     2.6123        80.0%
0.950000     2.7890        60.0%
```

### 3.5 其他调优示例

**调优 GMS 算法的温度衰减系数 r：**

```yaml
# tune_gms.yaml
algo: 1
parameter: "r"
start: 0.4
end: 0.9
step: 0.1
num_runs: 10
fixed:
  k: 40
  t0_block_divisor: 100.0
```

```bash
python test_scripts.py --tune tune_gms.yaml --white_space_ratio 0.1
```

**调优 FastSA 的 EWMA 平滑系数 alpha：**

```yaml
# tune_fastsa.yaml
algo: 2
parameter: "ewma_alpha"
start: 0.05
end: 0.5
step: 0.05
num_runs: 5
```

---

## 常用示例

### 1. 基本 2 次实验

```bash
python test_scripts.py --num_runs 2 --white_space_ratio 0.15
```

### 2. 30 次实验 + 固定种子（可复现）

```bash
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 \
    --seed_file ./seeds/seeds_30_test1.txt
```

### 3. 曲线记录实验（最多 10 次）

```bash
python test_scripts.py --num_runs 10 --white_space_ratio 0.15 --record_curve
```

### 4. 算法切换（GMS 算法）

```bash
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 -a 1
```

### 5. 算法切换（FastSA 算法）

```bash
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 -a 2
```

### 6. 算法切换（GMS_FastSA 混合算法）

```bash
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 -a 3
```

### 7. 参数调优（SA 的 r 参数）

```bash
# 先创建 tune_config.yaml（见上方示例）
python test_scripts.py --tune tune_config.yaml --white_space_ratio 0.1
```

### 8. 调优 + 曲线记录（探索收敛行为）

```bash
python test_scripts.py --tune tune_config.yaml --white_space_ratio 0.1 --record_curve
```

### 9. 跳过编译（已编译过的情况）

```bash
python test_scripts.py --num_runs 20 --white_space_ratio 0.1 --skip_make
```

### 10. 完整自定义参数

```bash
python test_scripts.py \
    --executable ../bin/hw3_dbg \
    --hardblocks ./testcase/n200.hardblocks \
    --nets ./testcase/n200.nets \
    --terminals ./testcase/n200.pl \
    --white_space_ratio 0.2 \
    --num_runs 50 \
    --output_dir ./output/my_exp \
    --log_file ./log/my_exp.log \
    --seed_file ./seeds/my_seeds.txt \
    --skip_make \
    --record_curve \
    -a 1
```

### 11. 不同测试规模对比（n100 / n200 / n300）

```bash
# n100
python test_scripts.py --hardblocks ./testcase/n100.hardblocks \
    --nets ./testcase/n100.nets --terminals ./testcase/n100.pl \
    --num_runs 30 --white_space_ratio 0.1

# n200
python test_scripts.py --hardblocks ./testcase/n200.hardblocks \
    --nets ./testcase/n200.nets --terminals ./testcase/n200.pl \
    --num_runs 30 --white_space_ratio 0.1

# n300
python test_scripts.py --hardblocks ./testcase/n300.hardblocks \
    --nets ./testcase/n300.nets --terminals ./testcase/n300.pl \
    --num_runs 30 --white_space_ratio 0.1
```

### 12. 不同空白比对比

```bash
# white_space_ratio = 0.1
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 -a 0

# white_space_ratio = 0.15
python test_scripts.py --num_runs 30 --white_space_ratio 0.15 -a 0
```

---

## 输出文件结构

```
test_experimrnts/
├── test_scripts.py                  # 本脚本
├── test_scripts.md                  # 本文档
│
├── log/                             # 实验日志（原始输出 + 统计结果）
│   ├── running_results_algo0_2026-06-08_16:21:22.txt
│   ├── running_results_algo1_2026-06-08_17:00:00.txt
│   └── tune_algo0_r_2026-06-08_18:00:00/     # 调优模式的日志
│       ├── param_r0_5/
│       │   └── running_results_algo0_r0_5.txt
│       ├── param_r0_55/
│       │   └── running_results_algo0_r0_55.txt
│       └── summary.txt
│
├── output/                          # floorplan 输出文件
│   ├── test_100blocks_ratio_0_1_total_30_algo0/
│   │   ├── run1_algo0.floorplan
│   │   └── ...
│   └── tune_algo0_r_2026-06-08_18:00:00/
│       ├── val1_run1.floorplan
│       └── ...
│
├── config/                          # 调优模式生成的 JSON 配置
│   ├── tune_algo0_r0_5.json
│   └── tune_algo0_r0_55.json
│
├── seeds/                           # 保存的种子文件
│   └── seeds_30_algo0_2026-06-08.txt
│
└── results/
    └── curve_results/               # 曲线记录模式的数据
        ├── curve_data_algo0_2026-06-08_16:21:22/
        │   ├── curve_data_run1_algo0.csv
        │   └── ...
        └── tune_algo0_r_2026-06-08_18:00:00/
            └── ...                  # 调优+曲线模式的数据
```

---

## 注意事项

1. **首次运行**会自动执行 `make -f Makefile.debug` 编译，确保 `./cpp_src/` 目录下存在 Makefile。
2. **种子可复现**：使用 `--seed_file` 指定种子文件路径，可完全复现实验。种子生成算法：`(RANDOM << 15) + RANDOM`，范围 `[0, 2^30)`。
3. **曲线模式上限**：`--record_curve` 模式下 `--num_runs` 自动限制为最多 10 次，防止数据量过大。
4. **调优模式依赖**：`--tune` 需要安装 PyYAML：`pip install pyyaml`。
5. **调优+曲线**：同时使用 `--tune` 和 `--record_curve` 时，强制 `num_runs=1`、参数值最多 10 个。
6. **路径默认值**：所有路径相对于脚本所在目录（`test_experimrnts/`），自动解析为绝对路径。
7. **统计方法**：平均值/标准差计算前会剔除 IQR 异常值（`Q1 - 1.5*IQR` 到 `Q3 + 1.5*IQR` 之外的值）。
8. **日志文件**：每次实验的完整原始输出（stdout+stderr）都会保存在日志文件中，供后续排查。
9. **JSON 配置块名**：调优模式下，YAML 中的 `parameter` 必须与 C++ 程序 JSON 解析时的键名严格一致（大小写敏感）。算法模式与 JSON 块名的映射见上表。
