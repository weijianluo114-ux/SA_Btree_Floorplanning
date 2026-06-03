#include "utils.h"
#include <iostream>
#include <iomanip> // 用于 std::fixed, std::setprecision

using namespace std;

// 实时DEBUG函数
ConsoleRegion::ConsoleRegion(int lines) : lines_(lines) {}

void ConsoleRegion::update(const std::vector<std::string> &contents)
{
    if (first_update_)
    {
        // 预留 lines 行空白区域，并保存光标初始位置（可选，这里用相对回退法）
        for (int i = 0; i < lines_; ++i)
            std::cout << '\n';
        first_update_ = false;
    }
    // 光标上移 lines 行
    std::cout << "\033[" << lines_ << "A";
    // 逐行输出，并清除该行原有内容
    for (int i = 0; i < lines_; ++i)
    {
        std::cout << "\033[K" << contents[i] << '\n';
    }
    std::cout << std::flush;
}

// 函数计数器
ScopedTimer::ScopedTimer(std::string name)
    : name_(std::move(name)),
      start_(std::chrono::steady_clock::now()) {}

ScopedTimer::~ScopedTimer()
{
    auto end = std::chrono::steady_clock::now();
    auto dur = end - start_;
    using namespace std::chrono;

    // 总微秒数（整数）
    auto us_total = duration_cast<microseconds>(dur).count();

    std::cout << "[" << name_ << "] 耗时: ";
    if (us_total <= 1000)
    {
        // ≤1000 微秒：直接输出整数微秒
        std::cout << us_total << " us\n";
    }
    else if (us_total <= 1000000)
    {
        // >1000 且 ≤1,000,000 微秒：转换为毫秒，保留 3 位小数
        double ms = us_total / 1000.0;
        std::cout << std::fixed << std::setprecision(3) << ms << " ms\n";
    }
    else
    {
        // >1,000,000 微秒：转换为秒，保留 6 位小数
        double sec = us_total / 1000000.0;
        std::cout << std::fixed << std::setprecision(6) << sec << " s\n";
    }
}
