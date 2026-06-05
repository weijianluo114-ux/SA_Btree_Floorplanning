#include <vector>
#include <cstdlib>
#include <cmath>
#include <algorithm>

#include "GMS.h"

using namespace std;

BiasSelector::BiasSelector(int N) : n(N)
{
    prob.assign(n, vector<double>(n, 0.0));
    row_sum.assign(n, 0.0);
    total_sum = 0.0;
    init();
}

void BiasSelector::init()
{
    for (int i = 0; i < n; ++i)
    {
        for (int j = i + 1; j < n; ++j)
        {
            prob[i][j] = prob[j][i] = 1.0;
        }
        row_sum[i] = (n - 1) * 1.0; // 每行有 n-1 个非对角元素
    }
    total_sum = n * (n - 1) * 1.0;
}

void BiasSelector::update(int i, int j, double delta_cost, double T, bool accepted)
{
    if (i == j)
        return; // 旋转操作不更新 prob 矩阵

    double &p = prob[i][j];
    double reward = exp(-delta_cost / T);
    const double eta = 0.1;
    const double PROB_MIN = 0.5;
    const double PROB_MAX = 5.0;

    double old_p = p; // 更新后的 p 已经赋值

    if (accepted)
    {
        p += eta * (reward - 1.0);
    }
    else
    {
        p *= 0.95;
    }
    if (p < PROB_MIN)
        p = PROB_MIN;
    if (p > PROB_MAX)
        p = PROB_MAX;

    double new_p = p;
    prob[j][i] = new_p;

    // 增量更新 row_sum 和 total_sum
    double delta = new_p - old_p;
    row_sum[i] += delta;
    row_sum[j] += delta;
    total_sum += 2.0 * delta;
}

pair<int, int> BiasSelector::selectPair(double T, bool force_random)
{
    // 强制随机进行选择
    if (force_random)
    {
        int a = rand() % n;
        int b = rand() % n;
        while (a == b)
            b = rand() % n; // 保证不同模块
        return {a, b};
    }

    // 第一步：按 row_sum 权重选第一个模块 i (轮盘赌 O(n))
    double rand_val = ((double)rand() / RAND_MAX) * total_sum;
    double cum = 0.0;
    int i = 0;
    for (; i < n; ++i)
    {
        cum += row_sum[i];
        if (cum >= rand_val)
            break;
    }

    // 第二步：在第 i 行内，按 prob[i][k] 权重选第二个模块 j (j != i)
    double row_total = row_sum[i];
    rand_val = ((double)rand() / RAND_MAX) * row_total;
    cum = 0.0;
    int j = 0;
    for (; j < n; ++j)
    {
        if (j == i)
            continue;
        cum += prob[i][j];
        if (cum >= rand_val)
            break;
    }
    return {i, j};
}
