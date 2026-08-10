# test_debug.md — 脚本功能回归测试

> 目的：快速验证 `test_scripts.py` 及 `scripts/` 下绘图脚本的核心功能是否正常。
> 约定：一律使用 `n10` 电路（体积小、跑得快），测试产物都落在 `log/YYYY_MM_DD/HH-MM-SS_...` 下。
> 用法：按编号从上到下执行；每步有「预期」和「检查点」，打 ✅ 表示通过。

---

## 0. 准备

```bash
cd /data1/user23006/EDA/SA_Btree_Floorplanning
conda env create -f environment.yml   # 依赖检查（缺哪个先 pip install）
conda activate SA_Btree
```

> 每个实验的产物目录名形如 `19-30-56_n10_wsr010_a0_tot1`，可用 `log/latest` 快速定位最近一次运行。

---

## 1. 单次运行（批量模式）

```bash
python test_scripts.py --circuit n10 --num_runs 1 --white_space_ratio 0.1
```

**预期**：生成

```
log/2026_08_09/<HH-MM-SS>_n10_wsr010_a0_tot1/
    run.log  config.yaml  output/  figures/  curves/  seeds/
```

且 `log/latest` 指向该目录（`ls -l log/latest` 是软链接）。

**检查点**

- [X]  `log/latest` 存在并指向最新目录
- [X]  `run.log` 末尾有「最终结果」统计表，`Cost` 有数值
- [X]  `output/` 下有 `run1_*.floorplan` 和 `run1_*.Btree`（两个都在）
- [X]  `seeds/` 下有种子快照文件（1 行）
- [X]  `config.yaml` 内容正确（circuit=n10, algo=0, num_runs=1）
- [X]  所有文件名里**没有冒号 `:`**（时间戳应为 `..._HH-MM-SS` 格式）

---

## 2. 多次运行（统计功能）

```bash
python test_scripts.py --circuit n10 --num_runs 5 --white_space_ratio 0.1 -a 0 --skip_make
```

**检查点**

- [X]  `run.log` 里有 5 个 `Run i / 5` 块
- [X]  统计表中标准差不是 0（说明 5 次结果有差异）
- [X]  `seeds/` 快照文件有 5 行

---

## 3. 固定种子可复现

```bash
python test_scripts.py --circuit n10 --num_runs 5 --seed_file ./seeds/seeds_5.txt --skip_make
python test_scripts.py --circuit n10 --num_runs 5 --seed_file ./seeds/seeds_5.txt --skip_make   # 再跑一次同样命令
```

**检查点**

- [X]  两次运行最终的 `Cost` 完全一致（种子相同 → 结果相同）

---

## 4. 参数调优（--tune）

先建配置文件 `config/tune_config.yaml`：

```yaml
algo: 0                # SA
parameter: "r"         # 调温度衰减系数
start: 0.5
end: 0.9
step: 0.1
num_runs: 2            # 每个参数值跑 2 次（n10 很快）
```

运行：

```bash
python test_scripts.py --circuit n10 --tune ./config/tune_config.yaml --skip_make
```

**预期**：生成

```
log/2026_08_09/<HH-MM-SS>_tune_a0_r_0.5-0.9/
    param_r0_5/  param_r0_6/  ...  summary.txt
```

**检查点**

- [X]  存在 5 个 `param_*` 子目录，各含 1 个 `running_results_*.txt`
- [X]  `summary.txt` 有「参数值 / 平均Cost / 可行解率」表
- [X]  `config/tune_*.json` 临时文件**已被清理**（目录里没有残留）
- [X]  `log/latest` 已指向调优目录

---

## 5. 曲线记录（--record_curve）

```bash
python test_scripts.py --circuit n10 --num_runs 2 --white_space_ratio 0.1 --record_curve
```

**检查点**

- [X]  产物目录下 `curves/` 里有 `curve_data_run1_algo0.csv`、`curve_data_run2_algo0.csv`
- [X]  CSV 首行表头 = `width,height,area,wirelength,R,cost,Total_Moves,T_Moves,T_uphill,T_reject,T`
- [X]  CSV 有数据行（非空）

---

## 6. 集成绘图：floorplan / B*-tree（--draw_fp）

```bash
python test_scripts.py --circuit n10 --num_runs 1 --white_space_ratio 0.1 --draw_fp
```

**检查点**

- [X]  产物目录 `figures/` 下有 `run1_*_floorplan.png` 和 `run1_*_btree.png`
- [X]  图片非空（`ls -l` 大小 > 0）

---

## 7. 集成绘图：叠加网表（--draw_nets）

```bash
python test_scripts.py --circuit n10 --num_runs 1 --white_space_ratio 0.1 --draw_fp --draw_nets --max_nets_draw 5
```

**检查点**

- [X]  `figures/` 下同时有 `run1_*_floorplan.png`（无网表）和 `run1_*_floorplan_with_nets.png`（有网表）

---

## 8. 集成绘图：模拟退火曲线（--draw_curve）

```bash
python test_scripts.py --circuit n10 --num_runs 1 --white_space_ratio 0.1 --record_curve --draw_curve
```

**检查点**

- [X]  `figures/` 下出现曲线图（`*_heatmap_*.png`、`all_metrics_heatmap_*.png`）

---

## 9. 独立运行 `draw_fixed_outline.py`（单文件模式）

```bash
FP=$(ls log/latest/output/*.floorplan | head -1)
python scripts/draw_fixed_outline.py --floorplan "$FP"
```

**检查点**

- [ ]  与 `.floorplan` 同目录生成 `<stem>_floorplan.png`、`<stem>_btree.png`

---

## 10. 独立运行 `draw_fixed_outline.py`（批量模式，指定目录）

```bash
python scripts/draw_fixed_outline.py \
    --blocks 10 --ratio 0.1 --num_runs 1 --algo 0 \
    --floorplan_dir log/latest/output --output log/latest/figures
```

**检查点**

- [X]  打印「找到 N 对文件」，`log/latest/figures/` 下生成 png

> 批量模式默认会去旧目录 `output/test_10blocks_...` 找文件；新结构下必须用 `--floorplan_dir` 显式指定，否则会报「输出目录不存在」。

---

## 11. 独立运行 `draw_curve.py`

```bash
# 先进行曲线实验
python test_scripts.py --circuit n10 --num_runs 2 --white_space_ratio 0.1 --record_curve

# 方式 A：传入 curves 目录（自动找 curve_data_run*.csv）
python scripts/draw_curve.py --csv log/latest/curves --output_dir log/latest/figures

# 方式 B：传入单个 CSV
python scripts/draw_curve.py --csv log/latest/curves/curve_data_run1_algo0.csv --output_dir log/latest/figures
```

**检查点**

- [X]  在 `--output_dir` 下生成各指标的曲线图（`*_heatmap_*.png` 等）

---

## 12. 调优 + 曲线（组合场景）

```bash
python test_scripts.py --circuit n10 --tune ./config/tune_config.yaml --record_curve
```

**检查点**

- [X]  调优目录 `curves/` 下有 `param_r0_5/curve_data.csv` 等
- [X]  调优 `--record_curve` 时强制 `num_runs<=5`，参数值最多 10 个

---

## 13. 时间戳格式抽查（防路径坑）

```bash
find log -name "*:*" | head          # 应无输出（不允许冒号）
find log -type f -newer config/tune_config.yaml | grep -E "[0-9]{2}:[0-9]{2}:[0-9]{2}" | head
```

**检查点**

- [ ]  第一条命令无输出
- [ ]  所有时间戳均为 `YYYY-MM-DD_HH-MM-SS`（用连字符，非冒号）

---

## 结果记录表


| 编号 | 测试项                    | 通过? | 备注 |
| ------ | --------------------------- | ------- | ------ |
| 1    | 单次运行 + 目录结构       |       |      |
| 2    | 多次运行 + 统计           |       |      |
| 3    | 固定种子复现              |       |      |
| 4    | 参数调优                  |       |      |
| 5    | 曲线记录                  |       |      |
| 6    | 集成绘图 floorplan/Btree  |       |      |
| 7    | 叠加网表                  |       |      |
| 8    | 集成绘图曲线              |       |      |
| 9    | draw_fixed_outline 单文件 |       |      |
| 10   | draw_fixed_outline 批量   |       |      |
| 11   | draw_curve 独立运行       |       |      |
| 12   | 调优+曲线                 |       |      |
| 13   | 时间戳格式                |       |      |

---

## 常见失败排查


| 现象                      | 可能原因                         | 处理                                           |
| --------------------------- | ---------------------------------- | ------------------------------------------------ |
| 报「输出目录不存在」      | 绘图脚本没找到`.floorplan`       | 用`--floorplan_dir log/latest/output` 显式指定 |
| `output/` 下没有 `.Btree` | C++ 程序没输出 B-tree 文件       | 检查 hw3_dbg 是否在同一目录生成`.Btree`        |
| `draw_curve` 找不到 CSV   | 没开`--record_curve`，或路径写错 | 确认`curves/` 下有 `curve_data_run*.csv`       |
| `log/latest` 不是软链接   | 环境不支持符号链接               | 已回退为`log/latest.txt`（内容为相对路径）     |
| 文件名含冒号`:`           | 时间戳格式没统一                 | 全局把`%H:%M:%S` 改为 `%H-%M-%S`               |
| 跑调优报缺 PyYAML         | 依赖没装                         | `pip install pyyaml`                           |

> 提示：测试产生的旧目录可随时删除；`log/latest` 只指向最近一次，不影响历史数据。
