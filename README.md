# EDA实验说明手册

## 1.参考代码

### ①

[BTree + 模拟退火算法_b tree floorplan-CSDN博客](https://blog.csdn.net/mr_dec/article/details/124019823)

https://github.com/NewmiLeou/Fixed-outline-Floorplan-Design.git

（1）使用方法

**How to compile**

- In "src/" directory, type the command:

```bash
$ make
```

It will generate the executable file "hw3" in "bin\" directory.

- If you want to remove it please type the command:

```bash
$ make clean
```

**How to execute**

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

https://github.com/romulus0914/fixed-outline_floorplanning

## 2.参考论文

### ①

Modern Floorplanning Based on Fast Simulated Annealing
