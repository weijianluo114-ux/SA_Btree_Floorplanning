#各种变量的命名	
#定义变量 GXX，赋值为编译器 g++
GXX = g++	
#定义变量 GXXFLAG，内容为 -std=c++11，明确要求使用 C++11 标准
GXXFLAG = -std=c++11
#定义变量 FLAG -Wall：开启几乎所有常规警告，有利于代码质量	-O3：最高级别的优化，追求运行速度，可能增加编译时间和二进制体积。
FLAG = -Wall -O3

#定义源文件变量 SRC，指向唯一的实现文件
SRC = fixed-outline_floorplanning.cpp
#定义目标可执行文件名为 hw3
EXE = hw3

all::$(EXE)

$(EXE): $(SRC)
	$(GXX) $(GXXFLAG) $(FLAG) -o $@ $^

clean:
	rm -rf $(EXE)
