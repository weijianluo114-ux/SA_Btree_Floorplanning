
# test_scripts.py — 批量实验与参数调优脚本

> 本脚本统一了 floorplanning 的批量实验、曲线记录、参数调优和绘图入口。默认会根据 `--circuit` 自动选择 `./testcase/<circuit>.*`，并把结果按日期和时间戳归档到 `log/` 下。

---

## 目录

- [总览](#总览)
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

---

## 总览

最常用的命令只有四类：

```bash
# 1. 默认批量实验：自动选择 n10，运行 2 次
python test_scripts.py --num_runs 2 --white_space_ratio 0.15

# 2. 指定电路并记录曲线
python test_scripts.py --circuit n100 --num_runs 5 --white_space_ratio 0.1 --record_curve

# 3. 参数调优
python test_scripts.py --tune ./config/tune_config.yaml --white_space_ratio 0.1

# 4. 运行结束后自动绘制布局图及对应二叉树
python test_scripts.py --num_runs 10 --white_space_ratio 0.1 --draw_fp

# 5. 运行结束后记录曲线并绘制曲线图
python test_scripts.py --num_runs 10 --white_space_ratio 0.1 --draw_curve --record_curve
```

脚本会自动完成编译、种子管理、日志归档和结果统计；如果开启 `--draw_fp` 或 `--draw_curve`，还会在运行后调用 `scripts/` 下的绘图脚本。

---

## 命令行参数一览


| 参数                  | 类型  | 默认值          | 说明                                                                                     |
| ----------------------- | ------- | ----------------- | ------------------------------------------------------------------------------------------ |
| `--executable`        | str   | `./bin/hw3_dbg` | 可执行文件路径                                                                           |
| `--circuit`           | str   | `n10`           | 自动映射到`./testcase/<circuit>.hardblocks/.nets/.pl`，可选 `n10/n30/n50/n100/n200/n300` |
| `--white_space_ratio` | float | `0.1`           | 空白比例                                                                                 |
| `--num_runs`          | int   | `20`            | 运行次数                                                                                 |
| `--output_dir`        | str   | `None`          | floorplan 输出目录，默认由脚本自动创建                                                   |
| `--log_file`          | str   | `None`          | 完整日志文件路径，默认由脚本自动创建                                                     |
| `--seed_file`         | str   | `None`          | 种子文件路径，指定后可复现实验                                                           |
| `--skip_make`         | flag  | `False`         | 跳过`make -f Makefile.debug`                                                             |
| `--record_curve`      | flag  | `False`         | 记录模拟退火过程中的详细参数曲线                                                         |
| `-a` / `--algo`       | int   | `0`             | 算法模式（见下表）                                                                       |
| `--tune`              | str   | `None`          | 调优配置文件（YAML），触发参数调优模式                                                   |
| `--draw_fp`           | flag  | `False`         | 运行后自动绘制 floorplan 和 B*-tree                                                      |
| `--draw_curve`        | flag  | `False`         | 仅在`--record_curve` 模式下绘制曲线                                                      |
| `--draw_nets`         | flag  | `False`         | 绘制 floorplan 时叠加网表连线                                                            |
| `--max_nets_draw`     | int   | `None`          | 限制绘制的网表数量                                                                       |
| `--fp_dpi`            | int   | `120`           | floorplan 图片分辨率                                                                     |

> 当前版本不再使用 `--results_csv`，所有结果都写入日志和曲线文件。

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

各算法模块的可调参数都支持通过 JSON 配置文件（`--config`）覆盖。下面只保留关键参数，完整默认值以 C++ 实现为准。

### SA（algo 0）

关键参数：`P`、`r`、`epsilon`、`reject_rate`、`k`、`max_seconds_divisor`、`time_limit`、`t0_block_divisor`、`op_prob`。

### GMS（algo 1）

关键参数：`prob_rotate`、`prob_swap`、`prob_move`、`bias_explore_ratio`，以及 SA 的通用参数。

### FastSA（algo 2）

关键参数：`t1_amplify`、`P`、`c`、`k`、`max_iter`、`max_consecutive_reject`、`min_temp`、`sample_size`、`ewma_alpha`、`max_seconds_divisor`。

### GMS_FastSA（algo 3）

合并 GMS 和 FastSA 的参数，无独有参数。

### SawTooth_FastSA（algo 4）

关键参数：`stagnation_limit`、`REHEAT_DECAY`、`REHEAT_THRESHOLD`、`REHEAT_ROLLBACK_RATIO`，其余同 FastSA。

### GMS_DoubleMatrix（algo 5）

关键参数：`prob_rotate`、`prob_swap`、`prob_move`、`bias_explore_ratio`，其余同 SA。

### GMS_SawTooth_FastSA（algo 6）

合并 GMS 和 SawTooth_FastSA 的参数，无独有参数。

---

## 1. 批量实验模式

这是默认模式。脚本会运行 `--num_runs` 次实验，生成独立种子并汇总统计结果。

```bash
# 默认批量实验：n10，20 次，空白比 0.1
python test_scripts.py --num_runs 20 --white_space_ratio 0.1

# 指定电路和算法
python test_scripts.py --circuit n100 --num_runs 30 --white_space_ratio 0.15 -a 1
```

批量模式会把每次运行的原始输出写入 `log/YYYY_MM_DD/HH-MM-SS_<circuit>_wsr<ratio>_a<algo>_tot<num_runs>/run.log`，并把 `.floorplan` / `.Btree` 输出放到同一运行目录下的 `output/` 中。

---

## 2. 曲线记录模式

曲线模式会记录每次扰动对应的 CSV 数据，便于后续分析收敛过程。

```bash
# 记录曲线
python test_scripts.py --circuit n100 --num_runs 5 --white_space_ratio 0.1 --record_curve

# 记录曲线并切换算法
python test_scripts.py --circuit n100 --num_runs 5 --white_space_ratio 0.1 --record_curve -a 1
```

曲线 CSV 的列顺序为：`width,height,area,wirelength,R,cost,Total_Moves,T_Moves,T_uphill,T_reject,T`。

普通模式下可以再加 `--draw_curve` 自动绘图；调优模式下当前只建议使用 `--draw_fp`。

---

## 3. 参数调优模式

调优模式会根据 YAML 里的 `algo / parameter / start / end / step / num_runs / fixed` 做网格搜索。脚本会自动把参数名中的算法前缀去掉，例如 `SA.r` 会按 `r` 处理。

```yaml
algo: 0
parameter: "r"
start: 0.5
end: 0.95
step: 0.05
num_runs: 5
fixed:
  k: 40
  time_limit: 1195
```

```bash
# 基本调优
python test_scripts.py --tune ./config/tune_config.yaml --white_space_ratio 0.1

# 调优结束后自动绘制 floorplan / B*-tree
python test_scripts.py --tune ./config/tune_config.yaml --white_space_ratio 0.1 --draw_fp
```

调优模式的目录结构会落在 `log/YYYY_MM_DD/HH-MM-SS_tune_a{algo}_{param}_{start}-{end}/` 下，主要包含 `tune_log/param_*/run.log`、`output/param_*/run*.floorplan`、`curves/param_*/run*_curve_data.csv`、`seeds/param_*/seeds_*.txt`、`figures/` 和 `summary.txt`。

---

## 4. JSON 配置文件（直接使用）

C++ 程序支持通过 `--config <json_file>` 直接传入 JSON 配置文件来覆盖算法参数。调优模式下脚本会自动生成这类文件，也可以手动创建后直接运行二进制。

### 4.1 JSON 格式

```json
{
  "SA": { "r": 0.75, "k": 40, "time_limit": 600 },
  "GMS": { "prob_rotate": 0.1, "prob_swap": 0.8, "prob_move": 0.1, "bias_explore_ratio": 0.15 },
  "FastSA": { "t1_amplify": 150.0, "ewma_alpha": 0.3, "max_iter": 300000, "sample_size": 1500 }
}
```

### 4.2 手动运行 C++ 程序示例

```bash
./bin/hw3_dbg --algo 1 --config ./config/custom_config.json \
  ./testcase/n100.hardblocks ./testcase/n100.nets ./testcase/n100.pl \
  ./output/result.floorplan 0.1 12345
```

如果需要曲线输出，再加 `--curve`。Python 脚本当前不直接暴露 `--config`，通常通过调优模式间接生成。

---

## 常用示例

只保留最常用的几种命令：

```bash
# 默认批量实验
python test_scripts.py --num_runs 20 --white_space_ratio 0.1

# 记录曲线
python test_scripts.py --circuit n100 --num_runs 5 --white_space_ratio 0.1 --record_curve

# 参数调优
python test_scripts.py --tune ./config/tune_config.yaml --white_space_ratio 0.1 --draw_fp
```

---

## 输出文件结构

```text
log/YYYY_MM_DD/HH-MM-SS_<circuit>_wsr<ratio>_a<algo>_tot<num_runs>/
├── run.log
├── config.yaml
├── output/
│   ├── run1.floorplan
│   ├── run1.Btree
│   └── ...
├── curves/
│   ├── curve_data_run1_algo0.csv
│   └── ...
├── figures/
└── seeds/
    └── seeds_<num_runs>_algo<algo>_<timestamp>.txt

log/YYYY_MM_DD/HH-MM-SS_tune_a<algo>_<param>_<start>-<end>/
├── tune_log/param_*/run.log
├── output/param_*/run*.floorplan
├── curves/param_*/run*_curve_data.csv
├── seeds/param_*/seeds_*.txt
├── figures/
└── summary.txt
```

`.Btree` 文件和 `.floorplan` 文件会放在同一输出目录中，记录最终的 B*-tree 结构。

---

## 注意事项

1. 首次运行会自动执行 `make -f Makefile.debug`。
2. `--circuit` 优先于手动填写 `hardblocks / nets / terminals`，默认使用 `n10`。
3. `--record_curve` 主要用于普通批量模式；调优模式也会生成曲线文件，但当前只自动联动 `--draw_fp`。
4. 调优模式需要安装 PyYAML。
5. 除 `Feasible` 外，其余统计量只对可行解样本计算。
6. `--seed_file` 可复现实验；不提供时脚本会自动生成并保存种子文件。
