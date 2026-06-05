// Guided_Move_Selection.h
#ifndef GUIDED_MOVE_SELECTION_H
#define GUIDED_MOVE_SELECTION_H

#include <utility> // for std::pair
#include <vector>  // for std::vector

// 结构体声明
struct BiasSelector
{
    std::vector<std::vector<double>> prob; // 对称矩阵，只存 i<j（对角线不使用）
    std::vector<double> row_sum;           // 每行的和（不包括对角线）
    double total_sum;                      // 所有 row_sum 之和
    int n;

    BiasSelector(int N);
    void init(); // 初始化为 1.0
    void update(int i, int j, double delta_cost, double T, bool accepted);
    std::pair<int, int> selectPair(double T);
};

// 函数声明
// 根据概率矩阵和温度，有偏向地选择一对模块 (i,j)
// force_random = true 时完全随机选择（用于探索）

#endif // GUIDED_MOVE_SELECTION_H