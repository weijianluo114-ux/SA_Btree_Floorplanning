#ifndef UTILS_H
#define UTILS_H

// include
#include <string>
#include <vector>
#include <chrono>

class ConsoleRegion
{
    int lines_;
    bool first_update_ = true;

public:
    // 构造函数：指定要刷新的行数
    explicit ConsoleRegion(int lines);

    // 更新显示区域：传入 lines 行文本
    void update(const std::vector<std::string> &contents);
};

class ScopedTimer // 函数计时器
{
public:
    // 构造函数：传入测量段的名称
    explicit ScopedTimer(std::string name);

    // 析构函数：自动计算并输出耗时
    ~ScopedTimer();

    // 禁止拷贝与移动，避免误用
    ScopedTimer(const ScopedTimer &) = delete;
    ScopedTimer &operator=(const ScopedTimer &) = delete;

private:
    std::string name_;
    std::chrono::steady_clock::time_point start_;
};

#endif // UTILS_H