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
2. 1）固定轮廓约束：$\forall b_i \in B,0\le x_i \le w_{fl}-w_i\; $and $ 0 \le y_i \le h_{fl}-h_i$
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

2. *.soft**blocks*文件

```txt
NumSoftBlocks: 100	//总的软模块数
NumTerminals: 334	//总的端口数
sb0 softrectilinear 1419 0.1 10	//模块名字 softrectilinear 面积 宽高比下界 宽高比上界 
p1 terminal	//端口名 terminal
```

3. ***.net***文件

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
$ ./hw3 ../testcase/n100.hardblocks ../testcase/n100.nets ../ testcase/n100.pl ../output/n100_01.floorplan 0.1
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

不过，同步文件的话，vscode巨简单，直接在左边按同步更改的按钮即可

## 参考链接

[经典算法-B树&amp;B+树&amp;B*树（B Tree&amp;B+ Tree&amp;B Star Tree）_b树是向上合并-CSDN博客](https://blog.csdn.net/li975242487/article/details/90315858)

[B树(B-树) - 来由, 定义, 插入, 构建_哔哩哔哩_bilibili](https://www.bilibili.com/video/BV1tJ4m1w7yR/?spm_id_from=333.337.search-card.all.click&vd_source=d68838d6148730f6468477abb0cb56e6)

[B树 - 维基百科，自由的百科全书](https://zh.wikipedia.org/wiki/B%E6%A0%91)

[B+树 - 维基百科，自由的百科全书](https://zh.wikipedia.org/wiki/B%2B%E6%A0%91)

[B*树 - 维基百科，自由的百科全书](https://zh.wikipedia.org/wiki/B*%E6%A0%91)
