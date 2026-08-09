// test_utils.h
#ifndef TEST_UTILS_H
#define TEST_UTILS_H

// 包含你需要的标准库头文件
#include <vector>
#include <string>
#include <cstdint>

// 函数声明
std::vector<uint32_t> generate_seeds(int count);
std::string current_time_str();

// 类声明

// 常量声明（如果有）
extern const int DEFAULT_SEED_COUNT;

#endif // TEST_UTILS_H