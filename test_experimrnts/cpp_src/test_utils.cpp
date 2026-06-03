#include <random>
#include <fstream>
#include <vector>
#include <string>
#include <ctime>
#include <sstream>
#include <iomanip>
#include <iostream>

using namespace std;

// 全局变量声明
const int DEFAULT_SEED_COUNT = 100;

// 生成时间戳字符串（年-月-日-时-分）
std::string current_time_str()
{
    auto t = std::time(nullptr);
    auto tm = *std::localtime(&t);
    std::ostringstream oss;
    oss << std::setw(2) << std::setfill('0') << (tm.tm_year % 100) << '-'
        << std::setw(2) << std::setfill('0') << (tm.tm_mon + 1) << '-'
        << std::setw(2) << std::setfill('0') << tm.tm_mday << '-'
        << std::setw(2) << std::setfill('0') << tm.tm_hour << '-'
        << std::setw(2) << std::setfill('0') << tm.tm_min;
    return oss.str();
}

// 生成 seeds，并自动保存到 ./seeds/seeds_<timestamp>.txt
std::vector<uint32_t> generate_seeds(int count, string file_path)
{
    using namespace std;
    random_device rd;
    mt19937 gen(rd());
    uniform_int_distribution<uint32_t> dist;

    vector<uint32_t> seeds(count);
    for (auto &s : seeds)
        s = dist(gen);

    // 构造文件名
    string filename = file_path + current_time_str() + ".txt";
    ofstream fout(filename);
    if (!fout)
    {
        throw runtime_error("无法创建种子文件: " + filename);
    }
    for (auto s : seeds)
        fout << s << '\n';

    cout << "已生成 " << count << " 个种子，保存至 " << filename << endl;
    return seeds;
}