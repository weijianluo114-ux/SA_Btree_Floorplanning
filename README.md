# EDA实验说明手册

## 题目说明

### ①输入

1. 由m个硬模块（宽$w_i$和高$h_i$固定）组成的集合
2. 由m个软模块组成的集合，每一个$b_i$ in B有固定的面积$A_i$和限制的宽高比$R_i$($L_i\le R_i\le U_i$)(宽和高必须取整)
3. 空白率 `white_space_ratio`，预先输入的参数
   定义布图区域为正方形，并且所有blocks的面积已知为 `total_block_area`
   总的布线的宽度和高度计算：$w_{fl}=h_{fl}=\sqrt{total\_block\_area \times(1+white\_space\_ratio)}$
4. 坐标，左下角$(0,0)$，右上角$(w_{fl},h_{fl})$

### ②输出

1. 总互连线长：
   半周期线长（HPWL）定义：对每一个线网，找出该线网的所有引脚的最小包围矩形，此时$HPWL=最小包围矩形宽度+最小包围矩形高度$
2. 定义每一个模块的所有引脚都位于模块的中心点，e.g.:设模块左下角坐标为$(x_i,y_i)$（实数即可），则其中心点为$(x_i+w_i/2,y_i+h_i/2)$

### ③目标

1. 总线长WL和总运行时间RT最小
2. 1)固定轮廓约束：
   $ \forall b_i \in B,0\le x_i \le w_{fl}-w_i\; \ and\  0 \le y_i \le h_{fl}-h_i $

   2)任意2个模块不能重叠

### ④输入文件

1. *.hardblocks*文件

```txt
NumHardRectilinearBlocks: 100	//总的硬模块数
NumTerminals: 334	//总的端口数
sb0 hardrectilinear 4 (0, 0) (0, 33) (43, 33) (43, 0)	//模块名字 hardrectilinear 
顶点数 每个顶点的相对左下角的坐标（顺时针给出）
p1 terminal	//端口名 terminal
```

2. *.softblocks*文件

```txt
NumSoftBlocks: 100	//总的软模块数
NumTerminals: 334	//总的端口数
sb0 softrectilinear 1419 0.1 10	//模块名字 softrectilinear 面积 宽高比下界 宽高比上界 
p1 terminal	//端口名 terminal
```

3. *.net*文件

```txt
NumNets : 885	//网络总数
NumPins : 1873	//引脚总数
NetDegree : 2	//线网的“度”，即这个线网连接了几个引脚
//各个要连接的端口或模块的引脚
p1
sb26
```

4. ***.pl***文件

```txt
p1 0 0	//端口名 x坐标 y坐标
```

### ⑤输出文件

```txt
Wirelength 218352	//总的接线长度
Blocks
sb0 349 203 43 33 0	//块名称 左下角顶点x坐标 左下角顶点y坐标 宽度 高度 是否旋转
```

---

## 实验运行指南

### 1. 代码环境部署

#### 1.1 编译

所有实验通过 Python 脚本 test_scripts.py 驱动，它会自动调用 Makefile 完成编译。你也可以手动编译：

```bash
# 进入实验目录
cd test_experimrnts

# 手动编译（Debug 版本）（可选，python会自动编译）
make -f cpp_src/Makefile.debug

# 编译产物位于 ./bin/hw3_dbg
```

> **依赖项**：Python ≥ 3.6，推荐安装 PyYAML（用于参数调优模式）：
>
> ```bash
> # 安装 Python 依赖（matplotlib, pandas, PyYAML 等）
> pip install -r test_experimrnts/requirements.txt
> ```

#### 1.2 测试用例

项目包含 GSRC 基准测试集的 3 组标准用例，位于 `test_experimrnts/testcase/`：

| 用例 | 硬模块数 | 文件前缀   |
| ---- | -------- | ---------- |
| n100 | 100      | `n100.*` |
| n200 | 200      | `n200.*` |
| n300 | 300      | `n300.*` |

每组包含 `.hardblocks`（模块定义）、`.nets`（线网连接）、`.pl`（端口坐标）、`.softblocks`（软模块定义）四个文件。

---

### 2. 问题描述

**固定轮廓方形布图（Fixed-Outline Square Floorplanning）**：给定一组硬模块（宽度 $w_i$、高度 $h_i$ 固定）和空白率 $\rho$，将模块无重叠地放置于方形区域内。

- **布图区域**：正方形边长 $W = \sqrt{\text{总模块面积} \times (1 + \rho)}$
- **优化目标**：最小化总线长（HPWL）和运行时间
- **约束条件**：模块完全位于 $[0, W] \times [0, W]$ 内，且互不重叠

本项目实现了 **6 种模拟退火变体**（均基于 B\*-tree 表示）：

| 算法编号 | 算法名称                      | 核心特点                          |
| -------- | ----------------------------- | --------------------------------- |
| 0        | **SA（Classical SA）**  | 原始模拟退火，指数降温            |
| 1        | **GMS**                 | 引导矩阵偏置扰动选择 + SA         |
| 2        | **FastSA**              | 快速模拟退火，Cauchy 降温 + EWMA  |
| 3        | **GMS_FastSA**          | GMS 偏置选择 + FastSA 温度调度    |
| 4        | **SawTooth_FastSA**     | 锯齿形回火 FastSA（停滞检测回火） |
| 5        | **GMS_DoubleMatrix**    | 双矩阵 GMS（Swap/Move 分离）      |
| 6        | **GMS_SawTooth_FastSA** | GMS + 锯齿回火的完整组合          |

---

### 3. 最小 Demo 示例

以下命令均**在 `test_experimrnts/` 目录下执行**。默认空白率 `--white_space_ratio 0.1`。

#### 3.1 原始模拟退火（SA，algo 0）

```bash
# n100 数据集，运行 2 次，空白率 0.1
python test_scripts.py --num_runs 2 -a 0

# n200 数据集，运行 5 次
python test_scripts.py \
    --hardblocks ./testcase/n200.hardblocks \
    --nets ./testcase/n200.nets \
    --terminals ./testcase/n200.pl \
    --num_runs 5 -a 0
```

#### 3.2 快速模拟退火（FastSA，algo 2）

```bash
# n100 数据集，运行 5 次
python test_scripts.py --num_runs 5 -a 2

# n300 数据集，运行 3 次
python test_scripts.py \
    --hardblocks ./testcase/n300.hardblocks \
    --nets ./testcase/n300.nets \
    --terminals ./testcase/n300.pl \
    --num_runs 3 -a 2
```

#### 3.3 锯齿回火 FastSA（AST-FastSA / SawTooth_FastSA，algo 4）

```bash
# n100 数据集，运行 5 次
python test_scripts.py --num_runs 5 -a 4

# n200 数据集，运行 10 次
python test_scripts.py \
    --hardblocks ./testcase/n200.hardblocks \
    --nets ./testcase/n200.nets \
    --terminals ./testcase/n200.pl \
    --num_runs 10 -a 4
```

#### 3.4 GMS 增强算法（algo 1 / 3 / 6）

```bash
# GMS-SA（algo 1），n100，运行 5 次
python test_scripts.py --num_runs 5 -a 1

# GMS_FastSA（algo 3），n200，运行 5 次
python test_scripts.py \
    --hardblocks ./testcase/n200.hardblocks \
    --nets ./testcase/n200.nets \
    --terminals ./testcase/n200.pl \
    --num_runs 5 -a 3

# GMS_SawTooth_FastSA（algo 6，完整组合），n300，运行 3 次
python test_scripts.py \
    --hardblocks ./testcase/n300.hardblocks \
    --nets ./testcase/n300.nets \
    --terminals ./testcase/n300.pl \
    --num_runs 3 -a 6
```

#### 3.5 指定种子（可复现实验）

```bash
python test_scripts.py --num_runs 5 --seed_file ./seeds/seeds_5_test.txt -a 2
```

#### 3.6 曲线记录模式（记录收敛过程，最多 10 次）

```bash
python test_scripts.py --num_runs 5 --record_curve -a 4
```

---

### 4. 输出文件

#### 4.1 Floorplan 文件（`output/`）

运行后，每个 run 会在 `output/` 下生成一个按数据集和参数命名的子目录，例如：

```
output/test_100blocks_ratio_0_1_total_5_algo4/
├── run1_2026-06-11_15:17:54.floorplan   # 布图结果（模块坐标）
├── run1_2026-06-11_15:17:54.Btree       # B*-tree 结构
├── run2_2026-06-11_15:18:20.floorplan
├── run2_2026-06-11_15:18:20.Btree
└── ...
```

`.floorplan` 文件格式示例：

```
W:444
Wirelength :237949
Blocks:100
sb0 202 388 43 33 1    # 模块名 x y 宽 高 是否旋转(0/1)
sb1 350 78 65 37 0
...
```

#### 4.2 日志文件（`log/`）

运行结束后，脚本会在 `log/` 目录下生成完整的实验日志，文件命名格式为：

- `{算法}_{参数描述}_ratio{空白率}_test2.txt`
- 例如：`SawToothFastSA_b100_100_ratio_0.1_test2.txt`、`Original_b100_50_k20_d1_r090_ratio0.1_test2.txt`

日志文件结构如下：

```
==============================================
Batch floorplanning experiment
Hardblocks: .../n100.hardblocks
Nets:       .../n100.nets
Terminals:  .../n100.pl
Ratio:      0.1
Runs:       100
Start time: Thu Jun 11 20:27:44 2026
==============================================

============================================================
 Run 1 / 100  (seed = 151767152)
============================================================
Algorithm mode: 2
Total Block Area: 179501
Target Area:      197451
W:                444

Random seed: 151767152

[BuildInitBtree] 耗时: 7 us
Total runtime: 3.30369 seconds

Found feasible solution                          # 是否找到可行解
Width:      443
Height:     439
Area:       194477
Wirelength: 242455
R:          0.990971                              # 宽高比
Cost:       0.711066                              # 综合代价

[SimulatedAnnealing] 耗时: 3.488325 s

...（后续 run 同上结构）...

========== 统计结果 ==========
指标        平均值         标准差         ...       # 汇总统计表格
```

每条 run 记录包括：

- **输入参数**：算法模式、模块总面积、目标面积、轮廓宽度
- **运行信息**：随机种子、建树耗时（微秒）、总运行时间、SA 耗时（秒）
- **结果指标**：Width（实际宽度）、Height（实际高度）、Area（面积）、Wirelength（线长/HPWL）、R（宽高比）、Cost（综合代价）
- **可行解标记**：`Found feasible solution` 或 `Not Found feasible solution`
- **末尾汇总**：所有运行轮次的平均值、标准差、五数汇总（剔除 IQR 异常值），以及可行解统计（found / not found）

---

### 5. 深入了解

> 关于**批量实验参数详解**、**曲线记录与可视化**、**参数调优（网格搜索）**、**JSON 配置文件**、**各算法底层参数对照表**等完整说明，请参阅：
>
> 📄 **[test_experimrnts/test_scripts.md](./test_experimrnts/test_scripts.md)**

该文档详细涵盖以下内容：

- 全部命令行参数及其默认值
- 6 种算法模式及其 JSON 配置块名
- 每种算法的所有可调参数（SA 的 `P`/`r`/`k`、FastSA 的 `c`/`k`/`ewma_alpha`、SawTooth 的 `stagnation_limit`/`REHEAT_DECAY` 等）
- 参数调优（YAML 网格搜索）配置示例与输出目录结构
- 直接使用 JSON 配置文件运行 C++ 程序的方法
- 曲线 CSV 数据的绘图脚本示例
- 更多实际运行示例（不同数据集、不同空白率、不同运行次数）

---

### 6. 项目结构一览

```
GM-AST/
├── README.md                          # 本文档
├── GM-AST.md                          # 论文摘要与实验结果
├── test_experimrnts/                  # ★ 实验主目录
│   ├── test_scripts.py                #   实验驱动脚本（Python）
│   ├── test_scripts.md                #   脚本完整文档
│   ├── cpp_src/                       #   C++ 算法源码
│   │   ├── fixed-outline_floorplanning.cpp  # 主程序入口 + 6种算法
│   │   ├── GMS.cpp / GMS.h            #   引导矩阵（GM）实现
│   │   ├── utils.cpp / utils.h        #   工具函数
│   │   ├── test_utils.cpp/h           #   测试工具
│   │   ├── json.hpp                   #   JSON 解析（nlohmann/json）
│   │   └── Makefile.debug             #   Debug 编译配置
│   ├── bin/                           #   编译产物
│   │   └── hw3_dbg
│   ├── testcase/                      #   GSRC 基准测试集
│   ├── output/                        #   布图结果（.floorplan + .Btree）
│   ├── log/                           #   实验日志（完整统计）
│   ├── config/                        #   调优 YAML 配置
│   ├── seeds/                         #   随机种子文件
│   ├── results/                       #   曲线数据
│   ├── docs/                          #   实验设计文档
│   ├── scripts/                       #   辅助绘图脚本
│   └── verifier/                      #   结果验证工具
├── reference/                         # 参考代码与论文
└── assets/                            # 论文用图
```

## 参考代码

### ①

[BTree + 模拟退火算法_b tree floorplan-CSDN博客](https://blog.csdn.net/mr_dec/article/details/124019823)

[github链接](https://github.com/NewmiLeou/Fixed-outline-Floorplan-Design.git)

#### **How to compile**

- In "src/" directory, type the command:

```bash
$ make
```

It will generate the executable file "hw3" in "bin\" directory.

- If you want to remove it please type the command:

```bash
$ make clean
```

#### **How to execute**

- In "src/" directory, enter the following command:

Format:

```bash
$ ..bin/<exe> <hardblocks file> <nets file> <pl file> <output file> <dead_space_ratio>
```

e.g.:

```bash
$ ../bin/hw3 ../testcase/n100.hardblocks ../testcase/n100.nets ../testcase/n100.pl ../output/n100_01.floorplan 0.1
```

--**Note:** output file will generate in "output\" directory.

- In "bin/" directory, enter the following command:
  Format:

```bash
$ ./<exe> <hardblocks file> <nets file> <pl file> <output file> <dead_space_ratio>
```

e.g.:

```bash
$ ./hw3 ../testcase/n100.hardblocks ../testcase/n100.nets ../testcase/n100.pl ../output/n100_01.floorplan 0.1
```

--Note: output file will generate in "output\" directory.

### ②

[github链接](https://github.com/romulus0914/fixed-outline_floorplanning)

#### Compile

```bash
make
```

#### Execute

```bash
./hw3 <path/to/input_hardblocks> <path/to/input_nets> <path/to/input_pl> <path/to/output_floorplan> <white_space_ratio>
```

e.g.

```bash
./hw3 ../testcase/n100.hardblocks ../testcase/n100.nets ../testcase/n100.pl ../output/n100.floorplan 0.1
```

## 参考论文

#### （1）Modern Floorplanning Based on Fast Simulated Annealing

#### （2）B*-Trees: A New Representation for Non-Slicing Floorplans

## 常用命令

```bash
git switch -c 分支名字	#创建新分支
git switch 分支	#切换分支

#假设你想把 test 分支上的工作合并到主分支 main：
git switch main		#切换到目标分支（你想把代码合并到哪里，就切到哪里）
git pull origin main	#拉取最新的远程代码（避免冲突，如果是协作项目）
git merge test		#合并源分支
```

## 参考链接

[经典算法-B树&amp;B+树&amp;B*树（B Tree&amp;B+ Tree&amp;B Star Tree）_b树是向上合并-CSDN博客](https://blog.csdn.net/li975242487/article/details/90315858)

[B树(B-树) - 来由, 定义, 插入, 构建_哔哩哔哩_bilibili](https://www.bilibili.com/video/BV1tJ4m1w7yR/?spm_id_from=333.337.search-card.all.click&vd_source=d68838d6148730f6468477abb0cb56e6)

[B树 - 维基百科，自由的百科全书](https://zh.wikipedia.org/wiki/B%E6%A0%91)

[B+树 - 维基百科，自由的百科全书](https://zh.wikipedia.org/wiki/B%2B%E6%A0%91)

[B*树 - 维基百科，自由的百科全书](https://zh.wikipedia.org/wiki/B*%E6%A0%91)
