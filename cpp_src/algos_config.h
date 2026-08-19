#ifndef ALGOS_CONFIG_H
#define ALGOS_CONFIG_H

// ========== SA 算法配置 ==========
struct SA_config
{
    double P = 0.95;           // 初始接受概率，用于计算 T0
    double r = 0.85;           // 原始(b100)的：算法衰减系数
    double epsilon = 1e-4;     // 最低温度阈值
    double reject_rate = 0.99; // 最大拒绝率
    int k = 40;                // 每块试探次数系数 (N = k * num_hardblocks)
    // 操作概率 (当前为均匀 rand()%3，可扩展)
    double op_prob[3] = {1.0 / 3, 1.0 / 3, 1.0 / 3};
    double t0_block_divisor = 10.0; // T0 = -cost * (n / divisor) / log(P)
    int time_limit = 1195;          // 总运行时间上限 (秒)
    int max_seconds_divisor = 5;    // 阶段超时: max_seconds = (n / divisor)^2

    // —— 新代价函数权重（Huang et al. 2020 惩罚函数框架）——
    double alpha = 0.45;              // 面积项权重 α
    double beta = 0.45;               // 线长项权重 β
    double gamma = 1.0;               // 惩罚项权重 γ
    double target_aspect_ratio = 1.0; // 目标宽长比 W/H（支持 1/2/3，1=正方形）
};

// ========== FastSA 算法配置 ==========
struct FastSA_config
{
    double t1_amplify = 1.0;          // T1 放大系数: T1 = t1_amplify * |Δavg / ln(P)|
    double P = 0.997;                 // 初始接受概率，用于计算 T1
    double c = 100.0;                 // 论文推荐 c=100
    int k = 7;                        // 论文推荐 k=7
    int max_iter = 3000000;           // 最大迭代次数（安全上限）
    int max_consecutive_reject = 150; // 连续拒绝阈值
    double min_temp = 1e-5;           // 最低温度阈值
    int sample_size = 1000;           // 预采样大小
    double ewma_alpha = 0.4;          // EWMA 平滑系数
    int max_seconds_divisor = 5.0;    // 阶段超时: max_seconds = (n / divisor)^2

    // —— 新代价函数权重（Huang et al. 2020 惩罚函数框架）——
    double alpha = 0.45;              // 面积项权重 α
    double beta = 0.45;               // 线长项权重 β
    double gamma = 1.0;               // 惩罚项权重 γ
    double target_aspect_ratio = 1.0; // 目标宽长比 W/H（支持 1/2/3，1=正方形）
};

// ========== SawTooth_FastSA 算法配置 ==========
struct SawTooth_FastSA_config
{
    double t1_amplify = 1.0;

    // ——— 新增 ———
    int stagnation_limit = 250; // 连续无改进的迭代次数阈值，触发回火

    // 新参数定义
    double REHEAT_DECAY = 0.9;          // 回火幅度衰减
    int REHEAT_THRESHOLD = 100;         // 连续拒绝阈值
    double REHEAT_ROLLBACK_RATIO = 0.6; // 回火时 n 回退比例

    double P = 0.997;                 // 初始接受概率，用于计算 T1
    double c = 100.0;                 // 论文推荐 c=100
    int k = 7;                        // 论文推荐 k=7
    int max_iter = 3000000;           // 最大迭代次数（安全上限）
    int max_consecutive_reject = 150; // 连续拒绝阈值
    double min_temp = 1e-5;           // 最低温度阈值
    int sample_size = 1000;           // 预采样大小
    double ewma_alpha = 0.4;          // EWMA 平滑系数
    int max_seconds_divisor = 5.0;    // 阶段超时: max_seconds = (n / divisor)^2

    // —— 新代价函数权重（Huang et al. 2020 惩罚函数框架）——
    double alpha = 1.0;               // 面积项权重 α
    double beta = 0.0;                // 线长项权重 β
    double gamma = 1.0;               // 惩罚项权重 γ
    double target_aspect_ratio = 3.0; // 目标宽长比 W/H（支持 1/2/3，1=正方形）
};

#endif // ALGOS_CONFIG_H