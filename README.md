# EDA实验说明手册

## 1.参考代码

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

## 2.参考论文

#### （1）Modern Floorplanning Based on Fast Simulated Annealing

#### （2）B*-Trees: A New Representation for Non-Slicing Floorplans


## 3.常用命令

```bash
git switch -c 分支名字	#创建新分支
git switch 分支	#切换分支

#假设你想把 test 分支上的工作合并到主分支 main：
git switch main		#切换到目标分支（你想把代码合并到哪里，就切到哪里）
git pull origin main	#拉取最新的远程代码（避免冲突，如果是协作项目）
git merge test		#合并源分支
```

不过，同步文件的话，vscode巨简单，直接在左边按同步更改的按钮即可
