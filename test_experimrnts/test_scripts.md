# test_scripts.py — 批量实验与参数调优脚本

> 本脚本替代了原始的 Bash 批处理方案，提供**批量实验**、**曲线记录**、**参数调优**三大核心功能，并自动完成结果提取、统计分析和日志归档。

---

## 目录

- [快速开始](#快速开始)
- [命令行参数一览](#命令行参数一览)
- [算法模式对照表](#算法模式对照表)
- [C++ 底层参数说明](#c-底层参数说明)
- [批量实验模式](#1-批量实验模式)
- [曲线记录模式](#2-曲线记录模式)
- [参数调优模式](#3-参数调优模式)
- [JSON 配置文件（直接使用）](#4-json-配置文件直接使用)
- [常用示例](#常用示例)
- [输出文件结构](#输出文件结构)
- [注意事项](#注意事项)
- [变更日志](#变更日志)

---

## 快速开始

```bash
# 进入脚本目录（以下所有命令均在此目录下执行）
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


| 参数                  | 类型  | 默认值                       | 说明                                   |
| ----------------------- | ------- | ------------------------------ | ---------------------------------------- |
| `--executable`        | str   | `./bin/hw3_dbg`              | 可执行文件路径（相对于脚本目录）       |
| `--hardblocks`        | str   | `./testcase/n100.hardblocks` | hardblocks 文件路径                    |
| `--nets`              | str   | `./testcase/n100.nets`       | nets 文件路径                          |
| `--terminals`         | str   | `./testcase/n100.pl`         | terminals 文件路径                     |
| `--white_space_ratio` | float | `0.1`                        | 空白比例                               |
| `--num_runs`          | int   | `20`                         | 运行次数                               |
| `--output_dir`        | str   | `None`                       | floorplan 输出目录（自动生成）         |
| `--log_file`          | str   | `None`                       | 完整日志文件路径（自动生成）           |
| `--seed_file`         | str   | `None`                       | 种子文件路径（指定后可复现实验）       |
| `--skip_make`         | flag  | `False`                      | 跳过 make 编译步骤                     |
| `--record_curve`      | flag  | `False`                      | 记录模拟退火过程中的详细参数曲线       |
| `-a` / `--algo`       | int   | `0`                          | 算法模式（见下表）                     |
| `--tune`              | str   | `None`                       | 调优配置文件（YAML），触发参数调优模式 |

> **注意**：`--results_csv` 参数虽保留在 argparse 中，但对应的 CSV 写入代码已注释，当前版本不生成结果 CSV 文件。所有数据均在日志（`.txt`）中记录。

---

## 算法模式对照表


| `-a` 值 | 算法名称                | JSON 配置块名           | 说明                                 |
| --------- | ------------------------- | ------------------------- | -------------------------------------- |
| `0`     | **SA**                  | `"SA"`                  | 原始模拟退火算法                     |
| `1`     | **GMS**                 | `"GMS"`                 | Guided Move Selection + SA           |
| `2`     | **FastSA**              | `"FastSA"`              | 快速模拟退火（动态温度调度）         |
| `3`     | **GMS_FastSA**          | `"GMS_FastSA"`          | GMS 偏置选择 + FastSA 温度调度       |
| `4`     | **SawTooth_FastSA**     | `"SawTooth_FastSA"`     | 锯齿形回火 FastSA（停滞检测回火）    |
| `5`     | **GMS_DoubleMatrix**    | `"GMS_DoubleMatrix"`    | 双矩阵 GMS（Swap/Move 分离独立矩阵） |
| `6`     | **GMS_SawTooth_FastSA** | `"GMS_SawTooth_FastSA"` | GMS 偏置选择 + SawTooth 回火 FastSA  |

---

## C++ 底层参数说明

各算法模块的所有可调参数均支持通过 JSON 配置文件（`--config`）覆盖。以下是每个算法块支持的全部参数：

### SA（algo 0）— 配置块名 `"SA"`


| 参数                  | 类型   | 默认值          | 说明                                        |
| ----------------------- | -------- | ----------------- | --------------------------------------------- |
| `P`                   | double | 0.95            | 初始接受概率，用于计算 T0                   |
| `r`                   | double | 0.85            | 温度衰减系数（T *= r）                      |
| `epsilon`             | double | 0.0001          | 最低温度阈值                                |
| `reject_rate`         | double | 0.99            | 最大拒绝率（超过则停止退火）                |
| `k`                   | int    | 40              | 每块试探次数系数（N = k × num_hardblocks） |
| `max_seconds_divisor` | int    | 10              | 阶段超时: max_seconds = (n / divisor)²     |
| `time_limit`          | int    | 1195            | 总运行时间上限（秒）                        |
| `t0_block_divisor`    | double | 100.0           | T0 = -cost × (n / divisor) / log(P) 的分母 |
| `op_prob`             | array  | [1/3, 1/3, 1/3] | 操作概率 [旋转, 交换, 移动]                 |

### GMS（algo 1）— 配置块名 `"GMS"`


| 参数                                                                                                    | 类型   | 默认值       | 说明                              |
| --------------------------------------------------------------------------------------------------------- | -------- | -------------- | ----------------------------------- |
| `prob_rotate`                                                                                           | double | 0.1          | 旋转操作概率                      |
| `prob_swap`                                                                                             | double | 0.8          | 交换操作概率                      |
| `prob_move`                                                                                             | double | 0.1          | 移动操作概率                      |
| `bias_explore_ratio`                                                                                    | double | 0.1          | 纯随机探索概率（1−此为偏置概率） |
| `P` / `r` / `epsilon` / `reject_rate` / `k` / `max_seconds_divisor` / `time_limit` / `t0_block_divisor` | —     | 同 SA 默认值 |                                   |

### FastSA（algo 2）— 配置块名 `"FastSA"`


| 参数                     | 类型   | 默认值 | 说明                                             |
| -------------------------- | -------- | -------- | -------------------------------------------------- |
| `t1_amplify`             | double | 100.0  | T1 放大系数: T1 = t1_amplify ×\|Δavg / ln(P)\| |
| `P`                      | double | 0.95   | 初始接受概率，用于计算 T1                        |
| `c`                      | double | 100.0  | 论文推荐 c=100                                   |
| `k`                      | int    | 7      | 论文推荐 k=7                                     |
| `max_iter`               | int    | 200000 | 最大迭代次数（安全上限）                         |
| `max_consecutive_reject` | int    | 5000   | 连续拒绝阈值                                     |
| `min_temp`               | double | 1e-9   | 最低温度阈值                                     |
| `sample_size`            | int    | 1000   | 预采样大小                                       |
| `ewma_alpha`             | double | 0.4    | EWMA 平滑系数                                    |
| `max_seconds_divisor`    | int    | 10     | 阶段超时: max_seconds = (n / divisor)²          |

### GMS_FastSA（algo 3）— 配置块名 `"GMS_FastSA"`

合并 GMS 和 FastSA 的参数（同上），额外无独有参数。

### SawTooth_FastSA（algo 4）— 配置块名 `"SawTooth_FastSA"`


| 参数                    | 类型   | 默认值 | 说明                               |
| ------------------------- | -------- | -------- | ------------------------------------ |
| `stagnation_limit`      | int    | 250    | 连续无改进的迭代次数阈值，触发回火 |
| `REHEAT_DECAY`          | double | 0.9    | 回火幅度衰减系数                   |
| `REHEAT_THRESHOLD`      | int    | 100    | 连续拒绝阈值（旧版回火触发条件）   |
| `REHEAT_ROLLBACK_RATIO` | double | 0.6    | 回火时 temp_n 回退比例             |
| 其余同 FastSA           | —     | —     | 同上                               |

### GMS_DoubleMatrix（algo 5）— 配置块名 `"GMS_DoubleMatrix"`


| 参数                 | 类型   | 默认值 | 说明           |
| ---------------------- | -------- | -------- | ---------------- |
| `prob_rotate`        | double | 0.1    | 旋转操作概率   |
| `prob_swap`          | double | 0.8    | 交换操作概率   |
| `prob_move`          | double | 0.1    | 移动操作概率   |
| `bias_explore_ratio` | double | 0.1    | 纯随机探索概率 |
| 其余同 SA            | —     | —     | 同上           |

> 与 GMS（algo 1）的区别：Swap 和 Move 使用**独立的**两个 `BiasSelector` 矩阵。

### GMS_SawTooth_FastSA（algo 6）— 配置块名 `"GMS_SawTooth_FastSA"`

合并 GMS 和 SawTooth_FastSA 的所有参数（同上）。

---

## 1. 批量实验模式

这是默认模式。脚本会运行 `--num_runs` 次实验，生成独立种子，汇总统计结果。

```bash
# 基本批量实验（20 次，空白比 0.1）
python test_scripts.py --num_runs 20 --white_space_ratio 0.1

# 指定不同的测试数据集（n200，空白比 0.15）
python test_scripts.py \
    --hardblocks n200.hardblocks \
    --nets n200.nets \
    --terminals n200.pl \
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
> 曲线数据保存在 `./results/curve_results/` 目录下，每行 CSV 格式：
> `width,height,area,wirelength,R,cost,Total_Moves,T_Moves,T_uphill,T_reject,T`

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
parameter: "r"         # 要调优的参数名（对应 JSON 配置块中的键，无需加算法前缀）
start: 0.5             # 起始值
end: 0.95              # 结束值
step: 0.05             # 步长
num_runs: 5            # 每个参数值运行次数（不同种子）
fixed:                 # 固定参数（可选，覆盖结构体默认值）
  k: 40
  time_limit: 1195
```

> **参数名自动去前缀**：YAML 中的 `parameter` 若带有算法前缀（如 `"SA.r"`），脚本会自动剥离，只需写裸参数名 `"r"`，因为算法模式已由 `algo` 字段指定。但 `fixed` 中的键名必须**全匹配** JSON 配置块中的路径（如 `"k"` 而非 `"SA.k"`；若需跨块覆盖则可写全路径）。

### 3.2 运行调优

```bash
# 基本调优
python test_scripts.py --tune ./config/tune_config.yaml --white_space_ratio 0.1

# 调优 + 曲线记录（强制 num_runs=1，最多 10 个参数值）
python test_scripts.py --tune ./config/tune_config.yaml --white_space_ratio 0.1 --record_curve
```

### 3.3 输出目录结构

```
./log/tune_algo0_r_2026-06-08_16:21:22/       # 调优根日志目录
    param_r0_5/                                # 每个参数值一个文件夹
        running_results_algo0_r0_5.txt         # 原始输出 + 完整统计
    param_r0_55/
        running_results_algo0_r0_55.txt
    summary.txt                                # 整体汇总表格

./config/                                      # 自动生成的 JSON 配置文件（调优完成后自动清理）
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

### 3.5 各算法调优示例

---

**① 调优 SA 的温度衰减系数 r：**

```yaml
# tune_sa_r.yaml
algo: 0
parameter: "r"
start: 0.5
end: 0.95
step: 0.05
num_runs: 10
```

```bash
python test_scripts.py --tune tune_sa_r.yaml --white_space_ratio 0.1
```

---

**② 调优 SA 的初始接受概率 P：**

```yaml
# tune_sa_P.yaml
algo: 0
parameter: "P"
start: 0.8
end: 0.99
step: 0.01
num_runs: 10
```

```bash
python test_scripts.py --tune tune_sa_P.yaml --white_space_ratio 0.1
```

---

**③ 调优 SA 的试探次数系数 k：**

```yaml
# tune_sa_k.yaml
algo: 0
parameter: "k"
start: 10
end: 100
step: 10
num_runs: 5
```

```bash
python test_scripts.py --tune tune_sa_k.yaml --white_space_ratio 0.1
```

---

**④ 调优 GMS 的偏置探索比例：**

```yaml
# tune_gms_bias.yaml
algo: 1
parameter: "bias_explore_ratio"
start: 0.0
end: 0.5
step: 0.05
num_runs: 10
fixed:
  k: 40
  t0_block_divisor: 100.0
```

```bash
python test_scripts.py --tune tune_gms_bias.yaml --white_space_ratio 0.1
```

---

**⑤ 调优 FastSA 的 EWMA 平滑系数 alpha：**

```yaml
# tune_fastsa_alpha.yaml
algo: 2
parameter: "ewma_alpha"
start: 0.05
end: 0.5
step: 0.05
num_runs: 5
```

```bash
python test_scripts.py --tune tune_fastsa_alpha.yaml --white_space_ratio 0.1
```

---

**⑥ 调优 FastSA 的采样大小：**

```yaml
# tune_fastsa_sample.yaml
algo: 2
parameter: "sample_size"
start: 200
end: 2000
step: 200
num_runs: 5
```

```bash
python test_scripts.py --tune tune_fastsa_sample.yaml --white_space_ratio 0.1
```

---

**⑦ 调优 SawTooth_FastSA 的回火停滞阈值：**

```yaml
# tune_sawtooth_stagnation.yaml
algo: 4
parameter: "stagnation_limit"
start: 100
end: 500
step: 50
num_runs: 5
```

```bash
python test_scripts.py --tune tune_sawtooth_stagnation.yaml --white_space_ratio 0.1
```

---

**⑧ 调优 SawTooth_FastSA 的回火衰减系数：**

```yaml
# tune_sawtooth_decay.yaml
algo: 4
parameter: "REHEAT_DECAY"
start: 0.5
end: 0.95
step: 0.05
num_runs: 5
```

```bash
python test_scripts.py --tune tune_sawtooth_decay.yaml --white_space_ratio 0.1
```

---

**⑨ 调优 GMS_SawTooth_FastSA 的交换操作概率：**

```yaml
# tune_gms_sawtooth_swap.yaml
algo: 6
parameter: "prob_swap"
start: 0.5
end: 0.95
step: 0.05
num_runs: 5
fixed:
  prob_rotate: 0.05
  prob_move: 0.05
```

```bash
python test_scripts.py --tune tune_gms_sawtooth_swap.yaml --white_space_ratio 0.1
```

---

**⑩ 调优 GMS_DoubleMatrix 的 T0 块除数：**

```yaml
# tune_gms_dm_t0.yaml
algo: 5
parameter: "t0_block_divisor"
start: 50.0
end: 500.0
step: 50.0
num_runs: 5
```

```bash
python test_scripts.py --tune tune_gms_dm_t0.yaml --white_space_ratio 0.1
```

---

## 4. JSON 配置文件（直接使用）

C++ 程序支持通过 `--config <json_file>` 直接传入 JSON 配置文件来覆盖算法参数。调优模式下脚本会自动生成此类文件；也可以手动创建并直接运行。

### 4.1 JSON 格式

```json
{
  "SA": {
    "r": 0.75,
    "k": 40,
    "time_limit": 600
  },
  "GMS": {
    "prob_rotate": 0.1,
    "prob_swap": 0.8,
    "prob_move": 0.1,
    "bias_explore_ratio": 0.15,
    "r": 0.85,
    "k": 50
  },
  "FastSA": {
    "t1_amplify": 150.0,
    "ewma_alpha": 0.3,
    "max_iter": 300000,
    "sample_size": 1500
  },
  "SawTooth_FastSA": {
    "stagnation_limit": 200,
    "REHEAT_DECAY": 0.85,
    "REHEAT_ROLLBACK_RATIO": 0.5
  },
  "GMS_FastSA": {
    "prob_swap": 0.7,
    "bias_explore_ratio": 0.2,
    "c": 80.0
  },
  "GMS_DoubleMatrix": {
    "k": 30,
    "t0_block_divisor": 200.0
  },
  "GMS_SawTooth_FastSA": {
    "stagnation_limit": 150,
    "ewma_alpha": 0.5,
    "bias_explore_ratio": 0.1
  }
}
```

### 4.2 手动运行 C++ 程序示例

```bash
# 直接运行 C++ 二进制，不通过 Python 脚本
./bin/hw3_dbg --algo 1 --config ./config/custom_config.json \
    ./testcase/n100.hardblocks \
    ./testcase/n100.nets \
    ./testcase/n100.pl \
    ./output/result.floorplan \
    0.1 \
    12345

# 启用曲线输出模式（CSV 格式打印到 stdout）
./bin/hw3_dbg --algo 0 --curve \
    ./testcase/n100.hardblocks \
    ./testcase/n100.nets \
    ./testcase/n100.pl \
    ./output/curved.floorplan \
    0.1 \
    67890
```

### 4.3 通过 Python 脚本传递 JSON 配置

当前 Python 脚本暂未开放直接传递 `--config` 的接口，但可通过以下方式间接实现：

1. **调优模式**：在 YAML 的 `fixed` 字段中指定固定参数，脚本会自动生成 JSON 并传递。
2. **手动修改脚本**：在 `run_single` 调用前插入 `--config` 参数。

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

### 7. 算法切换（SawTooth_FastSA 锯齿回火）

```bash
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 -a 4
```

### 8. 算法切换（GMS_DoubleMatrix 双矩阵 GMS）

```bash
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 -a 5
```

### 9. 算法切换（GMS_SawTooth_FastSA 组合算法）

```bash
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 -a 6
```

### 10. 参数调优（SA 的 r 参数）

```bash
# 先创建 tune_config.yaml（见上方示例）
python test_scripts.py --tune ./config/tune_config.yaml --white_space_ratio 0.1
```

### 11. 调优 + 曲线记录（探索收敛行为）

```bash
python test_scripts.py --tune tune_config.yaml --white_space_ratio 0.1 --record_curve
```

### 12. 跳过编译（已编译过的情况）

```bash
python test_scripts.py --num_runs 20 --white_space_ratio 0.1 --skip_make
```

### 13. 完整自定义参数

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

### 14. 不同测试规模对比（n100 / n200 / n300）

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

### 15. 不同空白比对比

```bash
# white_space_ratio = 0.1
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 -a 0

# white_space_ratio = 0.15
python test_scripts.py --num_runs 30 --white_space_ratio 0.15 -a 0
```

### 16. 全部 7 种算法快速对比（各 10 次）

```bash
for algo in 0 1 2 3 4 5 6; do
    python test_scripts.py --num_runs 10 --white_space_ratio 0.1 -a $algo --skip_make
done
```

### 17. 使用自定义 JSON 配置文件运行

```bash
python test_scripts.py --num_runs 20 --white_space_ratio 0.1 -a 1 --skip_make
# 若要直接使用 JSON 配置，需手动修改 test_scripts.py 或直接调用二进制：
./bin/hw3_dbg --algo 1 --config ./config/custom_config.json \
    ./testcase/n100.hardblocks \
    ./testcase/n100.nets \
    ./testcase/n100.pl \
    ./output/manual.floorplan \
    0.1 12345
```

### 18. 调优 SawTooth_FastSA 的停滞阈值（stagnation_limit）

```bash
# 配置文件见上节示例⑦
python test_scripts.py --tune tune_sawtooth_stagnation.yaml --white_space_ratio 0.1
```

### 19. 调优 GMS 算法操作概率组合

```yaml
# tune_gms_probs.yaml
algo: 1
parameter: "prob_swap"
start: 0.4
end: 0.95
step: 0.05
num_runs: 10
fixed:
  prob_rotate: 0.05
  prob_move: 0.05
```

```bash
python test_scripts.py --tune tune_gms_probs.yaml --white_space_ratio 0.1
```

### 20. 使用种子文件精确复现实验

```bash
# 先生成一批种子
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 --seed_file ./seeds/my_seeds.txt
# 用同样种子 + 不同算法复现对比
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 -a 1 --seed_file ./seeds/my_seeds.txt --skip_make
python test_scripts.py --num_runs 30 --white_space_ratio 0.1 -a 2 --seed_file ./seeds/my_seeds.txt --skip_make
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
├── output/                          # floorplan 输出文件（.floorplan + .Btree）
│   ├── test_100blocks_ratio_0_1_total_30_algo0/
│   │   ├── run1_algo0.floorplan
│   │   ├── run1_algo0.Btree          # ← 新增：B*-tree 结构文件
│   │   └── ...
│   └── tune_algo0_r_2026-06-08_18:00:00/
│       ├── val1_run1.floorplan
│       └── ...
│
├── config/                          # 调优模式生成的 JSON 配置（运行后自动清理）
│   ├── tune_algo0_r0_5.json
│   └── tune_algo0_r0_55.json
│
├── seeds/                           # 保存的种子文件
│   ├── seeds_30_algo0_2026-06-08.txt
│   ├── seeds_100.txt
│   ├── seeds_100_test1.txt
│   └── ...
│
└── results/
    └── curve_results/               # 曲线记录模式的数据
        ├── curve_data_algo0_2026-06-08_16:21:22/
        │   ├── curve_data_run1_algo0.csv
        │   └── ...
        └── tune_algo0_r_2026-06-08_18:00:00/
            └── ...                  # 调优+曲线模式的数据
```

> **注**：除了 `.floorplan` 文件，C++ 程序还会在**同一目录**下输出同名的 `.Btree` 文件，记录最终解的 B*-tree 结构（根节点编号及每个节点的 parent / left_child / right_child）。

---

## 注意事项

1. **首次运行**会自动执行 `make -f Makefile.debug` 编译，确保 cpp_src 目录下存在 Makefile.debug。
2. **种子可复现**：使用 `--seed_file` 指定种子文件路径，可完全复现实验。种子生成算法：`(RANDOM << 15) + RANDOM`，范围 `[0, 2^30)`。
3. **曲线模式上限**：`--record_curve` 模式下 `--num_runs` 自动限制为最多 10 次，防止数据量过大。
4. **调优模式依赖**：`--tune` 需要安装 PyYAML：`pip install pyyaml`。
5. **调优+曲线**：同时使用 `--tune` 和 `--record_curve` 时，强制 `num_runs=1`、参数值最多 10 个。
6. **路径默认值**：所有路径相对于脚本所在目录（`test_experimrnts/`），自动解析为绝对路径。
7. **统计方法**：平均值/标准差计算前会剔除 IQR 异常值（`Q1 - 1.5×IQR` 到 `Q3 + 1.5×IQR` 之外的值）。**注意**：除 Feasible 外的指标仅统计 **可行解（Feasible=1）** 的数据；Feasible 自身统计全部运行次数（反映真实成功率）。
8. **日志文件**：每次实验的完整原始输出（stdout+stderr）都会保存在日志文件中，供后续排查。
9. **JSON 配置块名**：调优模式下，YAML 中的 `parameter` 必须与 C++ 程序 JSON 解析时的键名严格一致（大小写敏感）。算法模式与 JSON 块名的映射见上表。参数名中的算法前缀（如 `"SA.r"`）会被自动剥离。
10. **`--results_csv` 已停用**：该参数仍可解析但代码中对应的 CSV 写入功能已被注释，所有数据仅保存到日志文件（`.txt`）。
11. **CSV 曲线格式**：曲线模式下每行 CSV 包含 `width,height,area,wirelength,R,cost,Total_Moves,T_Moves,T_uphill,T_reject,T`，其中 `T_Moves` / `T_uphill` / `T_reject` 为当前温度层内的计数器。
12. **调优模式会自动清理临时 JSON**：每个参数值运行时生成的临时 JSON 配置文件会在调优结束后自动删除（位于 `./config/tune_*.json`）。
13. **.Btree 文件**：每次运行结束后，程序会在输出目录生成 `.Btree` 文件（与 `.floorplan` 同路径），记录最终 B*-tree 结构，可用于分析树拓扑或断点恢复。

---

## 变更日志


| 版本 | 日期       | 变更内容                                                                                                                                                                                                         |
| ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| v2.0 | 2026-06-20 | 添加 algo 6 (GMS_SawTooth_FastSA)；补充各算法全部可调参数表；新增 JSON 配置用法章节；添加 20+ 条常用示例；补充`.Btree` 输出文件说明；修正统计方法说明（可行解过滤）；标注 `--results_csv` 已停用；补充注意事项。 |
| v1.0 | —         | 初始版本。                                                                                                                                                                                                       |
