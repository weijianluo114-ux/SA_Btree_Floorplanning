# SA-Btree Floorplanning 实验说明手册

本项目使用 B*-tree 表示硬模块布局，C++ 完成布局和模拟退火搜索，`test_scripts.py` 负责批量实验、统计、绘图、曲线记录、快照和参数调优。

## 1. 项目结构

```text
SA_Btree_Floorplanning/
├── README.md
├── test_scripts.py
├── cpp_src/
│   ├── fixed-outline_floorplanning.cpp
│   ├── utils.cpp / utils.h
│   ├── algos_config.h
│   ├── json.hpp
│   └── Makefile.debug
├── config/run_config.yaml
├── config/tune_config.yaml
├── testcase/
├── bin/
├── log/
├── output/
├── results/
├── scripts/
├── seeds/
└── verifier/
```

## 2. 环境和编译

需要 Linux、Python 3.6+、支持 C++11 的 `g++`。Python 功能使用 PyYAML，绘图功能使用 matplotlib 和 pandas：

```bash
pip install pyyaml matplotlib pandas
```

在项目根目录编译：

```bash
cd cpp_src
make -f Makefile.debug
```

编译产物为 `bin/hw3_dbg`。`test_scripts.py` 默认自动编译；已有可执行文件时可使用：

```bash
python test_scripts.py --skip_make
```

Makefile 支持以下编译模式：

```bash
make -f Makefile.debug CURVE_MODE=1
make -f Makefile.debug DEBUG_COST_LOG=1
make -f Makefile.debug SNAPSHOT_MODE=1
```

## 3. 输入文件和布局模型

当前主程序读取 `.hardblocks`、`.nets` 和 `.pl` 文件。`.hardblocks` 描述硬模块尺寸，`.nets` 描述网表连接关系，`.pl` 描述外部端口坐标。

`.softblocks` 可以保留在数据集目录中，但当前主程序运行路径使用硬模块输入，不会根据软模块面积和宽高比重新生成模块尺寸。

模块左下角为 `(x_i, y_i)`，宽高为 `w_i`、`h_i`，模块中心为：

$$
(x_i + w_i / 2,\ y_i + h_i / 2)
$$

每个网的 HPWL 为其连接点最小包围矩形的宽度和高度之和：

$$
HPWL = (x_{max} - x_{min}) + (y_{max} - y_{min})
$$

## 4. 固定轮廓约束

硬模块总面积为：

$$
A_{block} = \sum_i w_i h_i
$$

空白率为 `white_space_ratio` 时，目标面积为：

$$
A_{target} = A_{block} \times (1 + white\_space\_ratio)
$$

目标外框宽高比为 `W/H = target_aspect_ratio`。当宽高比为 `1` 时：

$$
W = H = \lceil \sqrt{A_{target}} \rceil
$$

布局必须满足模块不越界且任意两个模块不能重叠。

## 5. 当前算法模式

当前 Python 脚本和 C++ 主程序支持以下三种算法：

| 编号 | 算法 | 配置结构体 | 说明 |
|---:|---|---|---|
| `0` | SA | `SA_config` | 经典模拟退火 |
| `1` | FastSA | `FastSA_config` | 快速模拟退火 |
| `2` | SawTooth_FastSA | `SawTooth_FastSA_config` | 带停滞检测和回火的快速模拟退火 |

具体算法参数以 `cpp_src/algos_config.h` 为准。

## 6. 使用 `test_scripts.py`

所有命令在项目根目录执行：

```bash
python test_scripts.py
```

当前 `config/run_config.yaml` 的默认值为：

```yaml
circuit: n50
white_space_ratio: 0.1
target_aspect_ratio: 1
num_runs: 1
algo: 2
```

即默认使用 `n50`、空白率 `0.1`、正方形外框、SawTooth_FastSA，并运行一次。

常用命令：

```bash
# SA，n100，运行 5 次
python test_scripts.py --circuit n100 --num_runs 5 --white_space_ratio 0.1 --algo 0

# FastSA
python test_scripts.py --circuit n100 --num_runs 5 --algo 1

# SawTooth_FastSA
python test_scripts.py --circuit n100 --num_runs 5 --algo 2

# 跳过编译
python test_scripts.py --circuit n100 --num_runs 5 --skip_make
```

使用 `--circuit` 时，脚本自动查找：

```text
./testcase/<circuit>.hardblocks
./testcase/<circuit>.nets
./testcase/<circuit>.pl
```

当前目录中常见的数据集包括 `n10`、`n30`、`n50`、`n100`、`n200`、`n300`、`ami33`、`ami49`、`apte`、`hp` 和 `xerox`。自定义参数以 `python test_scripts.py --help` 输出为准。

## 7. `run_config.yaml`

配置文件控制数据集、算法、运行次数、绘图、曲线、快照、种子和输出目录。常用字段包括：

```yaml
circuit: n50
white_space_ratio: 0.1
target_aspect_ratio: 1
num_runs: 1
algo: 2
draw_init_floorplan: true
draw_fp: true
draw_btree: false
draw_curve: false
snapshot: false
snapshot_step: 10000
record_curve: false
redraw: false
redraw_output: null
debug_log: false
use_seed: true
seed_file: null
skip_make: false
draw_nets: false
max_nets_draw: null
fp_dpi: 120
tune: false
tune_config: ./config/tune_config.yaml
color_by_net: false
```

`draw_init_floorplan`、`draw_fp`、`draw_btree`、`draw_curve` 和 `draw_nets` 分别控制初始化布局、最终布局、B*-tree、退火曲线和网表的绘制。`max_nets_draw` 用于限制绘制的网数，`record_curve` 记录退火中间数据，`snapshot` 按 `snapshot_step` 保存中间布局，`redraw` 只对已有结果补绘制，`use_seed` 和 `seed_file` 控制随机种子复现。

## 8. 曲线、快照和调优

记录退火曲线：

```bash
python test_scripts.py --circuit n100 --num_runs 5 --algo 2 --record_curve
```

曲线 CSV 字段为：

```text
width,height,area,wirelength,R,cost,Total_Moves,T_Moves,T_uphill,T_reject,T
```

快照配置示例：

```yaml
snapshot: true
snapshot_step: 10000
```

调优配置文件为 `config/tune_config.yaml`：

```yaml
algo: 0
parameter: "alpha"
start: 0.0
end: 0.4
step: 0.1
num_runs_per_value: 10
fixed: {}
```

启动调优：

```bash
python test_scripts.py --tune ./config/tune_config.yaml --circuit n50
```

调优算法编号只能使用 `0`、`1` 或 `2`，参数名称和默认字段以 `cpp_src/algos_config.h` 为准。

## 9. C++ 程序直接运行

基本格式：

```bash
./bin/hw3_dbg \
    --algo 2 \
    ./testcase/n100.hardblocks \
    ./testcase/n100.nets \
    ./testcase/n100.pl \
    ./output/n100.floorplan \
    0.1 \
    12345
```

带 JSON 配置：

```bash
./bin/hw3_dbg \
    --algo 0 \
    --config ./config/custom_config.json \
    ./testcase/n100.hardblocks \
    ./testcase/n100.nets \
    ./testcase/n100.pl \
    ./output/result.floorplan \
    0.1 \
    12345
```

位置参数顺序为：

```text
hardblocks nets terminals output_floorplan white_space_ratio [seed]
```

主要选项为 `--algo`、`--config`、`--snapshot_step`、`--snapshot_fp`、`--snapshot_btree` 和 `--aspect_ratio`。注意：C++ 当前保留 `--aspect_ratio` 作为兼容参数，但源码会忽略该命令行值；实际目标宽高比来自算法配置结构体默认值或 JSON 配置文件。

## 10. 输出和统计

批量实验按日期和时间归档到 `log/`，每个实验目录通常包含运行日志、配置快照、`makefile.log`、`output/`、`curves/`、`figures/` 和 `seeds/`。

Python 脚本解析并统计 `Width`、`Height`、`Area`、`Wirelength`、`R`、`Cost`、`BTree_T_us`、`SA_T_s` 和 `Feasible`。统计结果包括平均值、标准差、IQR 异常值剔除后的五数汇总，以及可行解和不可行解分组统计。

程序会输出：

```text
Found feasible solution
```

或：

```text
Not Found feasible solution
```

`.floorplan` 文件示例：

```text
W:444
Wirelength :237949
Blocks:100
sb0 202 388 43 33 1
sb1 350 78 65 37 0
```

模块行字段依次为：模块名、左下角坐标、宽度、高度和旋转标志。

## 11. 常见实验流程

```bash
# 运行实验
python test_scripts.py --circuit n50 --num_runs 5 --algo 2

# 记录曲线
python test_scripts.py --circuit n50 --num_runs 5 --algo 2 --record_curve

# 参数调优
python test_scripts.py --tune ./config/tune_config.yaml --circuit n50

# 补绘制：先在 config/run_config.yaml 中设置 redraw 和 redraw_output
python test_scripts.py
```

## 12. 注意事项

1. 建议在项目根目录执行命令。
2. 修改 C++ 源码、头文件或编译模式后，应重新编译。
3. 当前算法编号仅支持 `0`、`1` 和 `2`。
4. 曲线和快照模式会增加运行时间、输出量和磁盘占用。
5. 网数较多时，使用 `max_nets_draw` 限制绘图规模。
6. 随机种子文件应保证每行是一个有效整数。
7. 算法参数以 `cpp_src/algos_config.h` 和 C++ 实现为准。
