#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <queue>

#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <ctime>

//----------------new include---------------------------//
#include "utils.h"
#include "GMS.h"
#include <chrono> // 如果原来没有
#include <sstream>
#include <tuple>
#include <cstring>

//------------------------------------------------------//

using namespace std;

//---------------------new MACRO------------------------//
// #define DEBUG 1
#define CURVE_MODE 1

//======================================================//

// --------------------- new struct ------------------------//
//  ========== SA 算法配置 ==========
struct SA_config
{
    double P = 0.95;              // 初始接受概率，用于计算 T0
    double r = 0.90;              // 温度衰减系数
    double epsilon = 0.0001;      // 最低温度阈值
    double reject_rate = 0.99;    // 最大拒绝率
    int k = 20;                   // 每块试探次数系数 (N = k * num_hardblocks)
    int max_seconds_divisor = 10; // 阶段超时: max_seconds = (n / divisor)^2
    int time_limit = 1195;        // 总运行时间上限 (秒)
    // 操作概率 (当前为均匀 rand()%3，可扩展)
    // double op_prob[3] = {1.0/3, 1.0/3, 1.0/3};
};

// ========== GMS 算法配置 ==========
struct GMS_config
{
    // 操作概率
    double prob_rotate = 0.1; // 旋转操作的概率
    double prob_swap = 0.8;   // 交换操作的概率
    double prob_move = 0.1;   // 移动操作的概率
    // 偏置探索
    double bias_explore_ratio = 0.1; // 纯随机探索概率
    // SA 参数
    double P = 0.95;           // 初始接受概率，用于计算 T0
    double r = 0.8;            // 温度衰减系数
    double epsilon = 0.0001;   // 最低温度阈值
    double reject_rate = 0.99; // 最大拒绝率
    int k = 40;                // 每块试探次数系数 (N = k * num_hardblocks)
    // 超时参数
    int max_seconds_divisor = 20; // 阶段超时: max_seconds = (n / divisor)^2
    int time_limit = 1195;        // 总运行时间上限 (秒)
    // T0 公式中的分母 (GMS 特有)
    double t0_block_divisor = 100.0; // T0 = -cost * (n / divisor) / log(P)
};

// ========== FastSA 算法配置 ==========
struct FastSA_config
{
    double P = 0.95;                   // 初始接受概率，用于计算 T1
    double c = 100.0;                  // 论文推荐 c=100
    int k = 7;                         // 论文推荐 k=7
    int max_iter = 200000;             // 最大迭代次数（安全上限）
    int max_consecutive_reject = 5000; // 连续拒绝阈值
    double min_temp = 1e-9;            // 最低温度阈值
    int sample_size = 1000;            // 预采样大小
    double ewma_alpha = 0.1;           // EWMA 平滑系数
    int max_seconds_divisor = 10;      // 阶段超时: max_seconds = (n / divisor)^2
};

//======================================================//

typedef struct hardblock
{
    int id;
    int x;
    int y;
    int width;
    int height;
    int rotate;
} HardBlock;

typedef struct terminal
{
    int id;
    int x;
    int y;
} Terminal;

// B树的结构体
typedef struct node
{
    int parent;
    int left_child;
    int right_child;
} Node;

typedef struct cost
{
    int width;
    int height;
    double area;
    double wirelength;
    double R;
    double cost;
} Cost;

// 新定义的参数和变量--------------------------------------------------------
#if CURVE_MODE
u_int32_t Total_Moves;  // 记录总的扰动次数
u_int32_t T_Moves = 0;  // 某个温度下已经尝试了多少次移动。通常理解为 move trial count
u_int32_t T_uphill = 0; // 某个温度下接受了多少次“更差”的解。用于控制当前温度下的搜索强度
u_int32_t T_reject = 0; // 某个温度下拒绝了多少次“更差”的解。用于控制当前温度下的搜索强度
#endif
double T;

// 全局控制标志
bool g_curve_mode = false; // 默认关闭曲线输出

//------------------------------------------------------------------------

int num_hardblocks, num_terminals; // 定义硬块数量和端点总数
int num_nets, num_pins;
vector<HardBlock> hardblocks;
vector<vector<int>> nets;
vector<Terminal> terminals;

double white_space_ratio;
double total_block_area; // 总硬块面积，即所有块加起来的面积和
// target area = total block area * (1 + white space ratio)
double area_target;
// area, wire length normalization = initial area, wirelength
double area_norm = 0, wl_norm = 0;
// fixed outline max x coordinate
int W;

// b*-tree
int root_block = -1;
vector<Node> btree;

// horizontal contour
vector<int> contour;

bool in_fixed_outline;
// floorplan with minimum cost
int min_cost_root_block;
Cost min_cost;
vector<HardBlock> min_cost_floorplan;
vector<Node> min_cost_btree;
// floorplan in fixed outline with minimum cost
int min_cost_root_block_fixed_outline;
Cost min_cost_fixed_outline;
vector<HardBlock> min_cost_floorplan_fixed_outline;
vector<Node> min_cost_btree_fixed_outline;

// 读取硬块文件
void ReadHardblocksFile(string hardblocks_file) // 接收参数为文件路径
{
    ifstream file;              // 创建一个输入文件流对象
    file.open(hardblocks_file); // 打开传进来的 hardblocks 文件，路径

    string temp1, temp2, str;                 // 创建一些临时的承接变量用于跳过不需要的量
    file >> temp1 >> temp2 >> num_hardblocks; // 从文件头读取前三项，其中最后一项是 hardblock 的数量
    file >> temp1 >> temp2 >> num_terminals;  // 读取 terminal 数量
    file >> str;                              // 读掉下一段内容，通常是表头或换行后的标记，避免后面解析时被干扰

    total_block_area = 0;                           // 初始化总硬块面积，用来后面累加
    hardblocks = vector<HardBlock>(num_hardblocks); // 创建一个大小为 hardblock 数量的数组，准备存每个块的信息
    for (int i = 0; i < num_hardblocks; i++)        // 开始逐个读取每个 hardblock 的尺寸信息
    {
        getline(file, str); // 读取当前这一整行内容到 str，因为这一行通常是类似描述块尺寸的文本格式

        size_t pos1 = str.find("(");    // 找第一个左括号的位置
        pos1 = str.find("(", pos1 + 1); // 再找下一个左括号
        pos1 = str.find("(", pos1 + 1); // 这说明这一行里可能有多个括号嵌套，真正要取的数据在第三个括号之后
        size_t pos2 = str.find(",");
        pos2 = str.find(",", pos2 + 1);
        pos2 = str.find(",", pos2 + 1); // 找到第三个逗号，这里是在定位 width 和 height 中间的分隔位置
        size_t pos3 = str.find(")");
        pos3 = str.find(")", pos3 + 1);
        pos3 = str.find(")", pos3 + 1); // 找第三个右括号

        char buffer[10];                                          // 准备一个短缓冲区，暂存切出来的数字字符串
        int width, height;                                        // 定义当前块的宽和高
        size_t len = str.copy(buffer, pos2 - pos1 - 1, pos1 + 1); // 从字符串中把宽度部分复制到 buffer 里
        buffer[len] = '\0';                                       // 手动补字符串结束符，变成 C 风格字符串
        width = atoi(buffer);
        len = str.copy(buffer, pos3 - pos2 - 2, pos2 + 2);
        buffer[len] = '\0';
        height = atoi(buffer);

        hardblocks[i].id = i;
        hardblocks[i].x = -1;
        hardblocks[i].y = -1;
        hardblocks[i].width = width;
        hardblocks[i].height = height;
        hardblocks[i].rotate = 0;

        total_block_area += width * height;
    }
    // store every block's trait, including weight, height, rotate and so on

    area_target = total_block_area * (1 + white_space_ratio);
    W = sqrt(area_target); // total floorplanning region width

    cout << "Total Block Area: " << total_block_area << '\n';
    cout << "Target Area:      " << area_target << '\n';
    cout << "W:                " << W << '\n';
    cout << '\n';

    file.close();
}

void ReadNetsFile(string nets_file)
{
    ifstream file;        // 定义类
    file.open(nets_file); // 打开网表文件

    // 读取NumNets和NumPins
    string temp1, temp2, str;
    file >> temp1 >> temp2 >> num_nets;
    file >> temp1 >> temp2 >> num_pins;

    // 建立一个大小为num_nets的数组，里面存放的是每一个网表中pin和block的id
    nets = vector<vector<int>>(num_nets);
    for (int i = 0; i < num_nets; i++)
    {
        int degree;
        file >> temp1 >> temp2 >> degree;
        for (int j = 0; j < degree; j++)
        {
            file >> str;
            int id;
            if (str[0] == 'p')
            {
                str.erase(0, 1);
                id = atoi(str.c_str()) + num_hardblocks; // 注意，这里pin的id要加上块的数量，以免搞混
            }
            else if (str[0] == 's')
            {
                str.erase(0, 2);
                id = atoi(str.c_str());
            }
            nets[i].emplace_back(id);
        }
    }

    file.close();
}

void ReadTerminalsFile(string terminals_file)
{
    ifstream file;
    file.open(terminals_file);

    string str;
    int x, y;

    terminals = vector<Terminal>(num_terminals + 1);
    for (int i = 1; i <= num_terminals; i++)
    {
        file >> str >> x >> y;
        terminals[i].id = i;
        terminals[i].x = x;
        terminals[i].y = y;
    }

    file.close();
}

void BuildInitBtree() // 更随机，更像纯拓扑初始化。
{
#ifdef DEBUG
    ScopedTimer t("BuildInitBtree");
#endif
    btree = vector<Node>(num_hardblocks); // 先开一个大小等于硬块数的节点数组，每个硬块先对应一个 Node 位置，后面会往里面填父子关系

    queue<int> bfs;                          // 定义一个队列，用来按层遍历树。这里的思路是后面从根开始，一层一层往下随机挂孩子
    vector<int> inserted(num_hardblocks, 0); // 定义一个标记数组，记录每个硬块有没有已经放进树里。0 表示没放，1 表示已经放过

    root_block = rand() % num_hardblocks; // 随机选一个硬块作为根节点。rand() % num_hardblocks 的结果范围是 0 到 num_hardblocks - 1
    btree[root_block].parent = -1;        // 根节点没有父亲，所以父节点设为 -1，这是个常见的“无效下标”标记
    bfs.push(root_block);                 // 把根节点放进队列，准备后面从它开始向下扩展
    inserted[root_block] = 1;             // 标记这个根节点已经被使用，避免后面又被随机选中重复插入

    int left = num_hardblocks - 1; // 除了根节点之外，还剩下多少个硬块没有放进树里。因为根已经用了一个，所以初值是总数减 1
    while (!bfs.empty())           // 只要队列里还有节点，就继续处理。队列里的节点就是当前已经放入树中的父节点，后面要给它们分配孩子。
    {
        int parent = bfs.front(); // 返回队首的引用     取出队首节点作为当前父节点，但还没有从队列删除它
        bfs.pop();                // 把刚才取出的父节点从队列中移除，表示它已经开始处理了

        int left_child = -1, right_child = -1; // 先把左右孩子都初始化成无效值，表示这个父节点一开始还没有孩子
        if (left > 0)                          // 如果还有没放进树里的硬块，就给当前父节点分配孩子
        {
            do
            {
                left_child = rand() % num_hardblocks;
            } while (inserted[left_child]); // 一直随机，直到找到一个没被插入过的节点

            btree[parent].left_child = left_child; // 把刚找到的节点挂到当前父节点的左边。
            bfs.push(left_child);                  // 把这个左孩子也放进队列，方便后面继续给它分配孩子
            inserted[left_child] = 1;              // 标记这个节点已经用过，防止后面再次随机选到它
            left--;                                // 剩余未插入的节点数减 1
            // 这一段是在判断是否还能再分配一个右孩子。如果还有剩余节点，就同样随机找一个没用过的节点作为右孩子，并挂到当前父节点右边
            if (left > 0)
            {
                do
                {
                    right_child = rand() % num_hardblocks;
                } while (inserted[right_child]);

                btree[parent].right_child = right_child; // 把随机得到的节点挂到右边
                bfs.push(right_child);                   // 把右孩子也放入队列，等待后续扩展
                inserted[right_child] = 1;
                left--;
            }
        }

        // 其实前面已经赋值过一次了，所以这里是重复赋值，功能上没有新增作用。
        btree[parent].left_child = left_child;
        btree[parent].right_child = right_child;
        if (left_child != -1)
            btree[left_child].parent = parent; // 如果左孩子确实存在，就设置它的父节点
        if (right_child != -1)
            btree[right_child].parent = parent; // 把左孩子的父指针指回当前父节点
    }
}

void InitBtree() // 更有约束，试图让初始树对应的 floorplan 更容易落进固定 outline。
{
#ifdef DEBUG
    ScopedTimer t("InitBtree");
#endif
    btree = vector<Node>(num_hardblocks);
    vector<int> inserted(num_hardblocks, 0);

    root_block = rand() % num_hardblocks;
    btree[root_block].parent = -1;
    inserted[root_block] = 1;

    int row_node = root_block;
    int col_node = root_block;
    int width = hardblocks[root_block].width;
    int inserted_cnt = 1;

    while (inserted_cnt != num_hardblocks)
    {
        int node;
        do
        {
            node = rand() % num_hardblocks;
        } while (inserted[node]);

        btree[node].left_child = -1;
        btree[node].right_child = -1;
        if (width > W)
        {
            btree[node].parent = row_node;
            btree[row_node].right_child = node;
            row_node = node;
            col_node = node;
            width = hardblocks[node].width;
        }
        else
        {
            btree[node].parent = col_node;
            btree[col_node].left_child = node;
            col_node = node;
            width += hardblocks[node].width;
        }

        inserted[node] = 1;
        inserted_cnt++;
    }
}

// 这个函数是在“递归给树上的每个块算坐标”。它的核心是：知道父块的位置后，按照 B*-tree 的规则，把当前块放到父块右边或上方，并更新轮廓线
void BtreePreorderTraverse(int cur_node, bool left)
{
    int parent = btree[cur_node].parent; // 取出当前节点的父节点编号，后面计算当前块坐标要用到父块的位置和尺寸
    // left or right child of parent
    if (left) // 这一段在算当前块的 x 坐标。如果它是左孩子，就放到父块右边，即横坐标加宽度
        hardblocks[cur_node].x = hardblocks[parent].x + hardblocks[parent].width;
    else
        hardblocks[cur_node].x = hardblocks[parent].x; // 如果它是右孩子，就和父块左边对齐，即横坐标相同

    int x_start = hardblocks[cur_node].x;             // 记录当前块左边界的 x 坐标，作为后面扫描轮廓线的起点
    int x_end = x_start + hardblocks[cur_node].width; // 计算当前块右边界的 x 坐标，也就是它占用的水平区间终点
    int y_max = 0;                                    // 初始化当前块应该放置的最低高度候选值，先从 0 开始
    // 这个循环在扫描当前块覆盖的水平区间 [[x_start, x_end)。
    // contour[i] 表示这个 x 位置已经被前面放置的块抬到的最高高度。
    // 这里找出这段区间里的最大轮廓高度，也就是当前块能贴着放下去的最低 y 位置。
    for (int i = x_start; i < x_end; i++)
    {
        if (i >= (int)contour.size())
        {
            cerr << "contour 越界: i=" << i << ", size=" << contour.size() << endl;
            contour.resize(i + 1000, 0); // 自动扩展
        }
        if (contour[i] > y_max)
            y_max = contour[i];
    }

    hardblocks[cur_node].y = y_max; // 把当前块的 y 坐标设为刚刚找到的最大轮廓高度，也就是它实际放置的位置。

    y_max += hardblocks[cur_node].height; // 当前块已经放上去了，所以把轮廓线抬高到当前块顶端。
    // 第二个写循环
    for (int i = x_start; i < x_end; i++)
    {
        if (i >= (int)contour.size())
            contour.resize(i + 1000, 0);
        contour[i] = y_max;
    } // 当前块已经放上去了，所以把轮廓线抬高到当前块顶端

    if (btree[cur_node].left_child != -1)
        BtreePreorderTraverse(btree[cur_node].left_child, true); // 如果当前节点还有左孩子，就递归处理左孩子，并传入 true。这表示左孩子要按“放到父块右边”的规则来算坐标。
    if (btree[cur_node].right_child != -1)
        BtreePreorderTraverse(btree[cur_node].right_child, false);
}

// 把当前的 B*-tree 重新“解码”成具体的版图坐标，也就是把树结构转换成每个硬块的 x、y 位置
void BtreeToFloorplan()
{
    contour = vector<int>(max(W * 5, num_hardblocks * 100), 0); // 初始化轮廓线数组。contour[i] 表示 x 位置 i 当前已经被占到的最高 y 值。这里开 W * 5 是给足够大的水平空间，避免越界。
    // 根节点在最左下角
    hardblocks[root_block].x = 0;
    hardblocks[root_block].y = 0;
    for (int i = 0; i < hardblocks[root_block].width; i++)
        contour[i] = hardblocks[root_block].height; // 把根块覆盖的水平范围标记起来。也就是说，根块占据了 [[0, width) 这段 x 区间，高度已经被抬到根块的顶端

    if (btree[root_block].left_child != -1)
        BtreePreorderTraverse(btree[root_block].left_child, true); // 如果根有左孩子，就从左孩子开始递归遍历。第二个参数 true 表示这个节点是父节点的左孩子
    if (btree[root_block].right_child != -1)
        BtreePreorderTraverse(btree[root_block].right_child, false); // 如果根有右孩子，也递归遍历。第二个参数 false 表示这个节点是父节点的右孩子
}

Cost CalculateCost()
{
    BtreeToFloorplan(); // 先把当前的 B*-tree 转成具体坐标。也就是说，先让每个硬块都有自己的 x、y 位置，后面才能统计整张图的尺寸。

    int width = 0, height = 0; // 初始化当前版图的外包矩形宽和高，先都设为 0，后面再遍历所有块去更新。
    // 这个循环在遍历所有硬块，找版图的最右边界和最上边界。
    // 如果某个块的右边界更大，就更新 width。
    // 如果某个块的上边界更大，就更新 height。
    // 最终得到的是整个 floorplan 的包围矩形尺寸。
    for (int i = 0; i < num_hardblocks; i++)
    {
        if (hardblocks[i].x + hardblocks[i].width > width)
            width = hardblocks[i].x + hardblocks[i].width;
        if (hardblocks[i].y + hardblocks[i].height > height)
            height = hardblocks[i].y + hardblocks[i].height;
    }

    // area of current floorplan
    double floorplan_area = width * height; // 计算当前 floorplan 的面积。这里用的是外包矩形面积，不是所有块真实面积之和。
    // aspect ratio of current floorplan
    double R = (double)height / width; // 计算当前版图的长宽比，也就是高度除以宽度。

    // half perimeter wire length   半周长线长
    double wirelength = 0;              // 初始化半周长线长的累加值。后面会遍历每一条 net，把每条 net 的 HPWL 加到这里。
    for (const vector<int> &net : nets) // 逐条遍历所有 net。net 是当前这条网表里连接的所有 pin 编号。
    {
        int x_min = width + 1, x_max = 0;
        int y_min = height + 1, y_max = 0;
        for (const int pin : net) // 这里的pin对应的是每一个要被连接的端口或模块的id，而比num_hardblocks下、数字小的是blocks，大的是teminal
        {
            if (pin < num_hardblocks) // 对blocks的处理
            {
                // 先计算中心点的位置
                int x_center = hardblocks[pin].x + hardblocks[pin].width / 2;
                int y_center = hardblocks[pin].y + hardblocks[pin].height / 2;
                // 再依次比较中心点位置是否比当前的矩形要小
                if (x_center < x_min)
                    x_min = x_center;
                if (y_center < y_min)
                    y_min = y_center;
                if (x_center > x_max)
                    x_max = x_center;
                if (y_center > y_max)
                    y_max = y_center;
            }
            else
            {
                const Terminal &t = terminals[pin - num_hardblocks]; // 引用terminals，以读取端口坐标
                if (t.x < x_min)
                    x_min = t.x;
                if (t.y < y_min)
                    y_min = t.y;
                if (t.x > x_max)
                    x_max = t.x;
                if (t.y > y_max)
                    y_max = t.y;
            }
        }

        wirelength += (x_max - x_min) + (y_max - y_min); // 计算HPWL
    }

    // 将当前的cost存储下来
    Cost c;
    c.width = width;
    c.height = height;
    c.area = floorplan_area;
    c.wirelength = wirelength;
    c.R = R;

    // set normalization to initial floorplan area and wirelength
    // 第一次进入这里时，把当前 floorplan 的面积记录为基准值 area_norm。
    // 这样后面所有面积代价都相当于“相对初始解的倍数”
    if (area_norm == 0)
        area_norm = floorplan_area;
    if (wl_norm == 0)
        wl_norm = wirelength; // 第一次进入这里时，把当前线长记录为基准值 wl_norm。后面线长代价也会按这个基准来归一化。

    double area_cost = c.area / area_norm;   // 计算面积代价。如果当前面积和初始面积一样，这项就是 1；如果更大，就大于 1
    double wl_cost = c.wirelength / wl_norm; // 计算线长代价，和面积代价一样，也是相对初始值的比例
    double R_cost = (1 - R) * (1 - R);       // 计算长宽比惩罚。这里希望 R 尽量接近 1，也就是版图尽量接近正方形；偏离 1 越多，惩罚越大
    // 先把宽和高的越界惩罚初始化为 0，默认不惩罚。
    double width_penalty = 0;
    double height_penalty = 0;
    if (width > W) // 如果当前版图宽度超过固定边界 W，就加宽度惩罚。超得越多，这项越大。
        width_penalty = ((double)width / W);
    if (height > W)
        height_penalty = ((double)height / W);
    c.cost = area_cost + wl_cost + R_cost + width_penalty + height_penalty; // 把所有代价项加起来，得到最终总成本。模拟退火后面就是用这个 c.cost 来判断当前布局好不好、要不要接受

// #ifdef DEBUG
//     cout << "Width:      " << c.width << '\n';
//     cout << "Height:     " << c.height << '\n';
//     cout << "Area:       " << c.area << '\n';
//     cout << "Wirelength: " << c.wirelength << '\n';
//     cout << "R:          " << c.R << '\n';
//     cout << "Cost:       " << area_cost << " + " << wl_cost << " + " << R_cost << " + "
//          << width_penalty << " + " << height_penalty << " = " << c.cost << '\n';
//     cout << '\n';
// #endif
// #ifdef DEBUG     //在批量运行的情况下把这个实时查看关闭
//     static auto last_update = std::chrono::steady_clock::now();
//     auto now = std::chrono::steady_clock::now();
//     double elapsed = std::chrono::duration<double>(now - last_update).count();
//     if (elapsed >= 1.0)
//     {
//         std::ostringstream oss;
//         oss << "\rCost:" << c.cost << " | Area:" << c.area
//             << " | WL:" << c.wirelength << " | W:" << c.width
//             << " H:" << c.height << " | R:" << c.R << "          ";
//         std::cout << oss.str() << std::flush;
//         last_update = now;
//     }
// #endif

// new--------------------------------
#if CURVE_MODE // 注意，以下会把每一次扰动的结果都记录下来，可能非常耗时
               // 新增：输出一行 CSV 格式的数据（换行结尾）
    // 使用 "CSV:" 前缀便于 Python 过滤
    if (g_curve_mode && T != 0)
    {
        std::cout << "CSV:"
                  << c.width << "," << c.height << ","
                  << c.area << "," << c.wirelength << ","
                  << c.R << "," << c.cost << ","
                  << Total_Moves << "," << T_Moves << ","
                  << T_uphill << "," << T_reject << ","
                  << T
                  << std::endl;
    }
#endif
    // -----------------------------------

    return c;
}

void Rotate(int node) // 简单的交换宽高操作
{
    int temp = hardblocks[node].width; // 定义一个名为 Rotate 的函数，参数 node 表示要旋转的硬块编号
    hardblocks[node].width = hardblocks[node].height;
    hardblocks[node].height = temp;
    hardblocks[node].rotate = 1 - hardblocks[node].rotate; // 如果原来是 0，就变成 1；如果原来是 1，就变成 0。
}

void Swap(int node1, int node2)
{
    // swap parent
    int node1_parent = btree[node1].parent; // 取出 node1 的父节点编号
    if (node1_parent != -1)                 // 如果 node1 不是根节点，就继续。因为根节点没有父节点，父编号是 -1
    {
        if (btree[node1_parent].left_child == node1) // 判断 node1 是不是它父节点的左孩子
            btree[node1_parent].left_child = node2;  // 如果是左孩子，就把父节点的左孩子改成 node2。
        else if (btree[node1_parent].right_child == node1)
            btree[node1_parent].right_child = node2; // 如果是右孩子，就把父节点的右孩子改成 node2。
        else                                         // 如果既不是左孩子也不是右孩子，就说明树结构已经不一致了。
        {
            cout << "[Error] node not parent's child\n";
            exit(1);
        }
    }

    int node2_parent = btree[node2].parent; // 取出 node2 的父节点编号，以下做同样的事情
    if (node2_parent != -1)
    {
        if (btree[node2_parent].left_child == node2)
            btree[node2_parent].left_child = node1;
        else if (btree[node2_parent].right_child == node2)
            btree[node2_parent].right_child = node1;
        else
        {
            cout << "[Error] node not parent's child\n";
            exit(1);
        }
    }

    // 交换2个节点的父母
    btree[node1].parent = node2_parent;
    btree[node2].parent = node1_parent;

    // swap children
    int node1_left_child = btree[node1].left_child;      // 先把 node1 的左孩子保存到临时变量里，避免后面覆盖掉
    int node1_right_child = btree[node1].right_child;    // 再把 node1 的右孩子保存起来
    btree[node1].left_child = btree[node2].left_child;   // 把 node2 的左孩子接到 node1 身上，也就是 node1 现在继承 node2 的左子树
    btree[node1].right_child = btree[node2].right_child; // 把 node2 的右孩子接到 node1 身上，也就是 node1 继承 node2 的右子树
    btree[node2].left_child = node1_left_child;          // 把原来 node1 的左孩子接到 node2 身上。
    btree[node2].right_child = node1_right_child;        // 把原来 node1 的右孩子接到 node2 身上

    // 以下是把被交换的节点的孩子的父母重新设置
    if (btree[node1].left_child != -1)                 // 如果 node1 还有左孩子，就继续处理
        btree[btree[node1].left_child].parent = node1; // 把 node1 的左孩子的父节点设成 node1。这样左孩子就知道自己现在挂在 node1 下面了。
    if (btree[node1].right_child != -1)
        btree[btree[node1].right_child].parent = node1;
    if (btree[node2].left_child != -1)
        btree[btree[node2].left_child].parent = node2;
    if (btree[node2].right_child != -1)
        btree[btree[node2].right_child].parent = node2;

    // node1, node2 are parent and child    父子关系
    if (btree[node1].parent == node1)          // 如果发现 node1 的 parent 变成了它自己，说明在交换过程中出现了“父指针自环”的临时状态。
        btree[node1].parent = node2;           // 把 node1 的父节点改成 node2。
    else if (btree[node1].left_child == node1) // 如果 node1 不是自己父亲，而是出现在自己的左孩子位置
        btree[node1].left_child = node2;       // 把 node1 的左孩子改成 node2。
    else if (btree[node1].right_child == node1)
        btree[node1].right_child = node2; // 把 node1 的右孩子改成 node2

    // 以下对node2进行同样的操作
    if (btree[node2].parent == node2)
        btree[node2].parent = node1;
    else if (btree[node2].left_child == node2)
        btree[node2].left_child = node1;
    else if (btree[node2].right_child == node2)
        btree[node2].right_child = node1;

    // root block may change
    // 如果交换后根节点发生变换，就把根节点变量替换
    if (node1 == root_block)
        root_block = node2;
    else if (node2 == root_block)
        root_block = node1;
}

void Move(int node, int to_node)
{
    // delete
    if (btree[node].left_child == -1 && btree[node].right_child == -1) // 判断这个节点是不是叶子节点，也就是左孩子和右孩子都不存在
    {
        // no children
        int parent = btree[node].parent;            // 先拿到它的父节点编号，后面要改父节点指向哪个孩子。
        if (btree[parent].left_child == node)       // 如果父节点的左孩子正好是这个 node。
            btree[parent].left_child = -1;          // 把父节点的左孩子改成 -1，表示这个位置现在空了
        else if (btree[parent].right_child == node) // 同理
            btree[parent].right_child = -1;
        else
        {
            cout << "[Error] node not parent's child\n";
            exit(1);
        }
    }
    else if (btree[node].left_child != -1 && btree[node].right_child != -1) // 判断当前节点是不是同时有左孩子和右孩子，也就是“有两个孩子”的情况。
    {
        // two children
        do
        {
            bool move_left; // 先定义一个布尔变量，决定这次要和左孩子换还是和右孩子换。
            if (btree[node].left_child != -1 && btree[node].right_child != -1)
                move_left = rand() % 2 == 0;       // 如果这个节点左右孩子都存在，就随机决定往左换还是往右换。
            else if (btree[node].left_child != -1) // 如果只有左孩子，就只能和左孩子换，所以设成 true。
                move_left = true;
            else
                move_left = false; // 否则就说明没有左孩子，那就只能和右孩子换，所以设成 false。

            if (move_left) // 如果要往左换，就把当前节点和左孩子交换。
                Swap(node, btree[node].left_child);
            else // 否则就把当前节点和右孩子交换。
                Swap(node, btree[node].right_child);
        } while (btree[node].left_child != -1 || btree[node].right_child != -1); // 循环条件，意思是只要当前节点还有任意一个孩子，就继续再换一次。

        // 把已经“沉到底”的节点，从它原来的父节点下面真正摘掉。即上面第1种情况
        int parent = btree[node].parent;
        if (btree[parent].left_child == node)
            btree[parent].left_child = -1;
        else if (btree[parent].right_child == node)
            btree[parent].right_child = -1;
        else
        {
            cout << "[Error] node not parent's child\n";
            exit(1);
        }
    }
    else
    {
        // one child
        int child; // 先定义一个临时变量 child，用来保存这个节点唯一的孩子。
        if (btree[node].left_child != -1)
            child = btree[node].left_child; // 如果左孩子存在，就把左孩子编号取出来。
        else
            child = btree[node].right_child; // 否则就说明唯一的孩子是右孩子，把右孩子编号取出来。

        int parent = btree[node].parent;
        if (parent != -1) // 如果它不是根节点，就继续更新父节点的孩子指针。
        {
            if (btree[parent].left_child == node)
                btree[parent].left_child = child;       // 如果父节点左孩子正好是当前节点，就把左孩子改成 child。
            else if (btree[parent].right_child == node) // 否则如果父节点右孩子正好是当前节点，就把右孩子改成 child
                btree[parent].right_child = child;
            else
            {
                cout << "[Error] [one child] node not parent's child\n";
                exit(1);
            }
        }

        btree[child].parent = parent; // 更新孩子的父母，完成交换

        // root block may change
        if (node == root_block) // 如果被删除的节点刚好是根节点，就把根更新成它的孩子。
            root_block = child;
    }

    // insert
    // 这段是在 Move 的“insert”阶段里，把已经删掉的 node 挂回到 to_node 下面。

    int random_left_right = rand() % 4; // 随机生成一个位置选择值，用来决定把 node 挂到 to_node 的哪一侧。
    int child;                          // 定义一个临时变量 child，保存 to_node 原来那个孩子。
    if (random_left_right == 0)         // 这次要把 node 插到 to_node 的左边。
    {
        child = btree[to_node].left_child; // 先把 to_node 原来的左孩子保存到 child，避免后面覆盖掉。
        btree[node].left_child = child;    // 把 child 接到 node 的左孩子位置，也就是让 node 继承原来左孩子那棵子树。
        btree[node].right_child = -1;      // 把 node 的右孩子设成 -1，表示它这次只作为一个左孩子插入。
        btree[to_node].left_child = node;  // 把 node 真正挂到 to_node 的左孩子位置。
    }
    else if (random_left_right == 1) // 这次要把 node 插到 to_node 的右边。
    {
        child = btree[to_node].right_child; // 先把 to_node 原来的右孩子保存到 child，避免后面覆盖掉。
        btree[node].left_child = child;     // 把 child 接到 node 的左孩子位置，也就是让 node 继承原来左孩子那棵子树。
        btree[node].right_child = -1;       // 把 node 的右孩子设成 -1，表示它这次只作为一个左孩子插入。
        btree[to_node].right_child = node;  // 把 node 真正挂到 to_node 的左孩子位置。
    }
    else if (random_left_right == 2) // 这次要把 node 插到 to_node 的左边。但孩子插在右边
    {
        child = btree[to_node].left_child;
        btree[node].left_child = -1;
        btree[node].right_child = child;
        btree[to_node].left_child = node;
    }
    else
    {
        child = btree[to_node].right_child;
        btree[node].left_child = -1;
        btree[node].right_child = child;
        btree[to_node].right_child = node;
    }
    btree[node].parent = to_node; // 把node的父节点更新
    if (child != -1)
        btree[child].parent = node; // 把孩子的父节点更新
}

// Verify 函数检查传入的版图 hb（所有硬块）的矩形是否两两重叠；若发现任意一对块有重叠，打印错误并退出程序。复杂度为 O(n^2)。
void Verify(vector<HardBlock> &hb)
{
    for (int i = 0; i < num_hardblocks; i++) // 外层循环，遍历每个硬块作为第1个矩形。
    {
        // 计算每个硬块的坐标
        int x_bl1 = hb[i].x;
        int y_bl1 = hb[i].y;
        int x_tr1 = x_bl1 + hb[i].width;
        int y_tr1 = y_bl1 + hb[i].height;
        for (int j = 0; j < num_hardblocks; j++) // 内层循环，遍历每个硬块作为第2个矩形（与第1个做比较）。
        {
            if (i == j)
                continue;

            // 计算第2个硬块的所有坐标
            int x_bl2 = hb[j].x;
            int y_bl2 = hb[j].y;
            int x_tr2 = x_bl2 + hb[j].width;
            int y_tr2 = y_bl2 + hb[j].height;

            // 判断是否重叠
            if (!(x_tr1 <= x_bl2 || x_bl1 >= x_tr2 || y_tr1 <= y_bl2 || y_bl1 >= y_tr2))
            {
                printf("[Error] hardblocks overlapped\n");
                exit(1);
            }
        }
    }
}

void SimulatedAnnealing(const SA_config &cfg)
{
#ifdef DEBUG
    ScopedTimer t("SimulatedAnnealing"); // 记录函数执行时间
#endif

// new----------------------------------------------
#if CURVE_MODE
    if (g_curve_mode)
    {
        Total_Moves = 0;
    }
#endif
    // new_end----------------------------------------------

    min_cost = CalculateCost();      // 先调用 CalculateCost 计算当前树对应的版图代价、宽高、面积、线长等，并把结果存进min_cost
    min_cost_floorplan = hardblocks; // 把当前这一版硬块布局复制到 min_cost_floorplan 里。hardblocks 里存的是每个块当前的坐标、宽高、旋转状态，所以这一步相当于把当前解的具体布局快照保存下来

    const double P = cfg.P;                     // 这是初始接受概率参数。它用于后面计算初始温度 T0，表示希望在一开始对较差解也有较高接受概率。
    const double r = cfg.r;                     // 温度衰减系数。每一轮大循环结束后，温度会乘上这个值，也就是 T *= r;，表示逐步降温。
    const double epsilon = cfg.epsilon;         // coolest temperature     //注释掉的最小温度阈值。原本可能想用它作为“冷却到某个程度就停止”的条件，但现在没用。
    const double reject_rate = cfg.reject_rate; // 拒绝率

    const int k = cfg.k;              // 每个硬块对应的试探次数系数。后面 N = k * num_hardblocks，表示每一轮允许的局部扰动规模和块数成正比。
    const int N = k * num_hardblocks; // 每一温度下的基础扰动上限
    // 初始温度。这个公式是根据“初始时差解接受概率约为 P”反推出来的。min_cost.cost 越大，初温越高；num_hardblocks 越多，初温也越高。
    const double T0 = -min_cost.cost * num_hardblocks / log(P);
    const int max_seconds = (num_hardblocks / cfg.max_seconds_divisor) * (num_hardblocks / cfg.max_seconds_divisor); // 一个按规模变化的阶段时间上限。块越多，这个值越大，允许搜索的单阶段时间越长。
    // const int max_seconds = 200;     // 一个按规模变化的阶段时间上限。块越多，这个值越大，允许搜索的单阶段时间越长。
    const int TIME_LIMIT = cfg.time_limit; // 20 minutes    总运行时间上限，约等于 20 分钟减 5 秒缓冲。避免程序跑太久。
    // 前者用于当前阶段超时判断，后者用于总时长限制
    int seconds = 0, runtime = 0; // seconds 表示自上次 time 起经过了多少秒；runtime 表示从 init_time 开始累计运行了多少秒

    // new-------------------------------------------------
    T = T0; // 当前温度，初始时等于 T0，后面每轮会下降
    // double operation_probs[3] = {0.1, 0.8, 0.1}; // 旋转, 交换, 移动
    // new_end----------------------------------------------

    int MT = 0;                // 当前温度下已经尝试了多少次移动。通常理解为 move trial count
    int uphill = 0;            // 当前温度下接受了多少次“更差”的解。用于控制当前温度下的搜索强度
    int reject = 0;            // 当前温度下拒绝了多少次候选解。这个变量在这里统计没被接受的操作数
    Cost prev_cost = min_cost; // 保存当前基准解的代价。后面每做一步扰动，都拿新代价和 prev_cost 比较
    in_fixed_outline = false;  // 先假设还没有找到满足固定外框的可行解。后面如果找到，就会改成 true

    clock_t init_time = clock(); // 记录模拟退火开始时的 CPU 时间，用来算总运行时间
    clock_t time = init_time;    // 记录“上一段计时起点”。后面如果超时但还没找到可行解，会重置这个时间点。

    do
    {
        MT = 0;
        uphill = 0;
        reject = 0;

// new----------------------------------------------
#if CURVE_MODE
        if (g_curve_mode)
        {
            T_Moves = 0;
            T_uphill = 0;
            T_reject = 0;
        }
#endif
        // new_end----------------------------------------------

        do
        {
            vector<HardBlock> hardblocks_temp(hardblocks); // 复制当前所有硬块的信息，作为临时备份。里面保存的是每个块当前的坐标、宽高、旋转状态等。
            vector<Node> btree_temp(btree);                // 复制当前 B*-tree 的结构，作为临时备份。里面保存的是每个节点的父子关系。
            int prev_root_block = root_block;              // 记录当前树的根节点编号。因为后面做 Swap 或 Move 时，根节点有可能变化，所以也要单独备份。

            // new----------------------------------------------
            // double op_rand = (double)rand() / RAND_MAX;
            // int M;
            // if (op_rand <= operation_probs[0]) // 旋转操作
            // {
            //     // rotate
            //     M = 0;
            //     // 随机选一个硬块节点 node，然后调用 Rotate 把它宽高交换，也就是块旋转 90 度。
            //     int node = rand() % num_hardblocks;
            //     Rotate(node);
            // }
            // else if (op_rand <= operation_probs[0] + operation_probs[1]) // 如果随机数是 1，就做 swap 操作。
            // {
            //     // swap
            //     M = 1;
            //     int node1, node2;
            //     // 先随机选 node1，再随机选一个和它不同的 node2，然后调用 Swap 交换这两个节点在树中的位置。
            //     node1 = rand() % num_hardblocks;
            //     do
            //     {
            //         node2 = rand() % num_hardblocks;
            //     } while (node2 == node1);
            //     Swap(node1, node2);
            // }
            // else if (op_rand <= operation_probs[0] + operation_probs[1] + operation_probs[2]) // move 操作
            // {
            //     M = 2;
            //     // move
            //     int node, to_node;
            //     // 先随机选一个要移动的节点 node，再随机选一个目标节点 to_node，但要保证
            //     // 这样是为了避免形成非法结构或立即构成环。最后调用 Move 把 node 挂到 to_node 下面。
            //     node = rand() % num_hardblocks;
            //     do
            //     {
            //         to_node = rand() % num_hardblocks;
            //     } while (to_node == node || btree[node].parent == to_node); // to_node != node      to_node 不能是 node 的父节点
            //     Move(node, to_node);
            // }
            // else // 这是兜底分支。按理说前面 rand() % 3 只会得到 0、1、2，所以这里不该进来。如果真的进来了，说明逻辑出了意外，程序直接报错退出。
            // {
            //     cout << "[Error] Unspecified Move\n";
            //     exit(1);
            // }
            // new_end----------------------------------------------

            // 这段是在每一轮扰动里，随机选择一种操作：旋转、交换、移动。它对应模拟退火里的“邻域搜索”。

            int M = rand() % 3; // 随机生成一个 0、1 或 2，用来决定这次要做哪一种操作。
            if (M == 0)         // 旋转操作
            {
                // rotate
                // 随机选一个硬块节点 node，然后调用 Rotate 把它宽高交换，也就是块旋转 90 度。
                int node = rand() % num_hardblocks;
                Rotate(node);
            }
            else if (M == 1) // 如果随机数是 1，就做 swap 操作。
            {
                // swap
                int node1, node2;
                // 先随机选 node1，再随机选一个和它不同的 node2，然后调用 Swap 交换这两个节点在树中的位置。
                node1 = rand() % num_hardblocks;
                do
                {
                    node2 = rand() % num_hardblocks;
                } while (node2 == node1);
                Swap(node1, node2);
            }
            else if (M == 2) // move 操作
            {
                // move
                int node, to_node;
                // 先随机选一个要移动的节点 node，再随机选一个目标节点 to_node，但要保证
                // 这样是为了避免形成非法结构或立即构成环。最后调用 Move 把 node 挂到 to_node 下面。
                node = rand() % num_hardblocks;
                do
                {
                    to_node = rand() % num_hardblocks;
                } while (to_node == node || btree[node].parent == to_node); // to_node != node      to_node 不能是 node 的父节点
                Move(node, to_node);
            }
            else // 这是兜底分支。按理说前面 rand() % 3 只会得到 0、1、2，所以这里不该进来。如果真的进来了，说明逻辑出了意外，程序直接报错退出。
            {
                cout << "[Error] Unspecified Move\n";
                exit(1);
            }

            // new----------------------------------------------
#if CURVE_MODE
            if (g_curve_mode)
            {
                Total_Moves++; // 实现总次数技计数
                T_Moves++;
            }
#endif
            // new_end----------------------------------------------

            MT++;                                                 // 增量计数当前温度层的尝试次数。
            Cost cur_cost = CalculateCost();                      // 计算做完扰动后的当前解代价。
            double delta_cost = cur_cost.cost - prev_cost.cost;   // 计算新解和当前基准解 prev_cost 之间的代价差；正值表示变差（更坏），负值表示变好（更优）。
            double random = ((double)rand()) / RAND_MAX;          // 生成一个 0 到 1 之间的随机浮点数，用于与 Metropolis 接受概率比较
            if (delta_cost <= 0 || random < exp(-delta_cost / T)) // 如果 delta_cost <= 0（变优或相等）或以概率 exp(-delta_cost / T) 接受变差解，则进入接受分支（Metropolis 准则）。
            {
                if (delta_cost > 0) // 若接受的是变差解（delta_cost > 0），则把 uphill++（记录当前温度下接受更差解的次数）。
                {
                    uphill++;

                    // new----------------------------------------------
#if CURVE_MODE
                    if (g_curve_mode)
                    {
                        T_uphill++;
                    }
#endif
                    // new_end----------------------------------------------
                }
                // feasible solution with minimum cost
                if (cur_cost.width <= W && cur_cost.height <= W) // 当 cur_cost.width <= W && cur_cost.height <= W 时视为落入固定外形（feasible）。
                {
                    if (in_fixed_outline)
                    {
                        if (cur_cost.cost < min_cost_fixed_outline.cost) // 如果已经有可行解（in_fixed_outline == true），且当前代价更小则更新可行解最优记录
                        {
                            min_cost_root_block_fixed_outline = root_block;
                            min_cost_fixed_outline = cur_cost;
                            min_cost_floorplan_fixed_outline = hardblocks;
                            min_cost_btree_fixed_outline = btree;
                        }
                    }
                    else
                    {
                        in_fixed_outline = true;                        // 标记可行解: in_fixed_outline = true; — 标记已经找到一个落入固定外形（宽高都 <= W）的可行解
                        min_cost_root_block_fixed_outline = root_block; // 记录当前解的根块编号，便于后续恢复/输出
                        min_cost_fixed_outline = cur_cost;              // 把当前计算得到的 Cost（宽、高、面积、线长、总代价等）保存为当前可行解的最优代价记录
                        min_cost_floorplan_fixed_outline = hardblocks;  // 复制并保存当前所有硬块的位置/尺寸/旋转状态，作为可行解的最优版图快照
                        min_cost_btree_fixed_outline = btree;           // 复制并保存当前的 B-树结构，作为可行解对应的树结构快照
                    }
                }

                // infeasible solution with minimum cost
                if (cur_cost.cost < min_cost.cost) // 若当前解的总代价更小，则更新“历史最优解”
                {
                    min_cost_root_block = root_block;
                    min_cost = cur_cost;
                    min_cost_floorplan = hardblocks;
                    min_cost_btree = btree;
                }

                prev_cost = cur_cost;
            }
            else
            {
                // new----------------------------------------------
#if CURVE_MODE
                if (g_curve_mode)
                {
                    T_reject++;
                }
#endif
                // new_end----------------------------------------------

                reject++;                     // 增加拒绝计数器（记录本次扰动被拒绝），用于后续停止/统计条件
                root_block = prev_root_block; // 把根节点恢复到扰动前的值（prev_root_block 在扰动前保存），以撤销可能的根变更
                if (M == 0)
                    hardblocks = hardblocks_temp; // 根据扰动类型恢复状态——当 M==0（旋转）只修改了 hardblocks，所以用 hardblocks_temp 回退
                else
                    btree = btree_temp; // 否则（swap 或 move）修改的是 btree，所以用 btree_temp 回退
            }
        } while (uphill <= N && MT <= 2 * N); // 当拒绝次数小于k*num_blocks并且扰动次数小于2倍的k*num_blocks就继续，即拒绝够多或者扰动够多就结束该温度下的扰动

        T *= r; // 降低温度

        seconds = (clock() - time) / CLOCKS_PER_SEC;      // 计算自上一次重置 time 以来经过的秒数。
        runtime = (clock() - init_time) / CLOCKS_PER_SEC; // 计算从模拟退火开始 (init_time) 到现在的总运行秒数。
        if (seconds >= max_seconds && in_fixed_outline == false)
        { // 如果本阶段耗时超过 max_seconds 并且还没找到可行解，则执行超时处理：
            cout << "Overtime " << min_cost.width << " " << min_cost.height << '\n';
            seconds = 0; // 将 seconds 清零并把 time 设为当前时刻（重置阶段计时器）
            time = clock();
            T = T0; // 将温度 T 重置为初始温度 T0（相当于在超时后重新从高温开始搜索）
        }
        // 当且仅当两个条件都满足时继续：
        // 拒绝率 (float)reject/MT 小于等于 0.95（拒绝太多则停止当前退火过程），
        // 当前温度 T 不低于阈值 epsilon（温度过低也会停止）。
    } while ((float)reject / MT <= reject_rate && T >= epsilon);
    // 下面表明曾有过以阶段耗时和总运行时间为停止条件的替代退出策略。
    //  } while (seconds < max_seconds && runtime < TIME_LIMIT);

    if (in_fixed_outline)
    {
        // 循环结束后（比如在 return 0 前）
#ifdef DEBUG
        std::cout << '\n';
#endif
        cout << "Found feasible solution\n";
        cout << "Width:      " << min_cost_fixed_outline.width << '\n';
        cout << "Height:     " << min_cost_fixed_outline.height << '\n';
        cout << "Area:       " << min_cost_fixed_outline.area << '\n';
        cout << "Wirelength: " << min_cost_fixed_outline.wirelength << '\n';
        cout << "R:          " << min_cost_fixed_outline.R << '\n';
        cout << "Cost:       " << min_cost_fixed_outline.cost << '\n';
        cout << '\n';

        Verify(min_cost_floorplan_fixed_outline); // 验证硬块的布局之间有无重叠
    }
    else
    {
        // 循环结束后（比如在 return 0 前）
#ifdef DEBUG
        std::cout << '\n';
#endif
        cout << "Not Found feasible solution\n";
        cout << "Width:      " << min_cost.width << '\n';
        cout << "Height:     " << min_cost.height << '\n';
        cout << "Area:       " << min_cost.area << '\n';
        cout << "Wirelength: " << min_cost.wirelength << '\n';
        cout << "R:          " << min_cost.R << '\n';
        cout << "Cost:       " << min_cost.cost << '\n';
        cout << '\n';

        Verify(min_cost_floorplan);
    }
}

void SimulatedAnnealing_GMS(const GMS_config &cfg)
{
#ifdef DEBUG
    ScopedTimer t("SimulatedAnnealing"); // 记录函数执行时间
#endif
    // new----------------------------------------------
#if CURVE_MODE
    if (g_curve_mode)
    {
        Total_Moves = 0;
    }
#endif
    // new_end----------------------------------------------

    //----------------------Guided Move Selection---------------------------//

    // 初始化
    BiasSelector selector(num_hardblocks);
    // double operation_probs[3] = {1.0, 0.0, 0.0}; // 旋转, 交换, 移动
    // double operation_probs[3] = {0.0, 1.0, 0.0}; // 旋转, 交换, 移动
    // double operation_probs[3] = {0.0, 0.0, 1.0}; // 旋转, 交换, 移动
    // double operation_probs[3] = {0.33, 0.34, 0.33}; // 旋转, 交换, 移动
    double operation_probs[3] = {cfg.prob_rotate, cfg.prob_swap, cfg.prob_move}; // 旋转, 交换, 移动
    double bias_explore_ratio = cfg.bias_explore_ratio;                          // 以0.1的概率完全随机探索，其余0.9概率使用偏置选择

    //----------------------------------------------------------------------//

    min_cost = CalculateCost();      // 先调用 CalculateCost 计算当前树对应的版图代价、宽高、面积、线长等，并把结果存进min_cost
    min_cost_floorplan = hardblocks; // 把当前这一版硬块布局复制到 min_cost_floorplan 里。hardblocks 里存的是每个块当前的坐标、宽高、旋转状态，所以这一步相当于把当前解的具体布局快照保存下来

    const double P = cfg.P;                     // 这是初始接受概率参数。它用于后面计算初始温度 T0，表示希望在一开始对较差解也有较高接受概率。
    const double r = cfg.r;                     // 温度衰减系数。每一轮大循环结束后，温度会乘上这个值，也就是 T *= r;，表示逐步降温。
    const double epsilon = cfg.epsilon;         // coolest temperature     //注释掉的最小温度阈值。原本可能想用它作为“冷却到某个程度就停止”的条件，但现在没用。
    const double reject_rate = cfg.reject_rate; // 拒绝率

    const int k = cfg.k;              // 每个硬块对应的试探次数系数。后面 N = k * num_hardblocks，表示每一轮允许的局部扰动规模和块数成正比。
    const int N = k * num_hardblocks; // 每一温度下的基础扰动上限
    // 初始温度。这个公式是根据“初始时差解接受概率约为 P”反推出来的。min_cost.cost 越大，初温越高；num_hardblocks 越多，初温也越高。
    const double T0 = -min_cost.cost * (num_hardblocks / cfg.t0_block_divisor) / log(P);
    const int max_seconds = (num_hardblocks / cfg.max_seconds_divisor) * (num_hardblocks / cfg.max_seconds_divisor); // 一个按规模变化的阶段时间上限。块越多，这个值越大，允许搜索的单阶段时间越长。
    // const int max_seconds = 200;     // 一个按规模变化的阶段时间上限。块越多，这个值越大，允许搜索的单阶段时间越长。
    const int TIME_LIMIT = cfg.time_limit; // 20 minutes    总运行时间上限，约等于 20 分钟减 5 秒缓冲。避免程序跑太久。
    // 前者用于当前阶段超时判断，后者用于总时长限制
    int seconds = 0, runtime = 0; // seconds 表示自上次 time 起经过了多少秒；runtime 表示从 init_time 开始累计运行了多少秒

    // new-------------------------------------------------
    T = T0; // 当前温度，初始时等于 T0，后面每轮会下降
    // new_end----------------------------------------------
    int MT = 0;                // 当前温度下已经尝试了多少次移动。通常理解为 move trial count
    int uphill = 0;            // 当前温度下接受了多少次“更差”的解。用于控制当前温度下的搜索强度
    int reject = 0;            // 当前温度下拒绝了多少次候选解。这个变量在这里统计没被接受的操作数
    Cost prev_cost = min_cost; // 保存当前基准解的代价。后面每做一步扰动，都拿新代价和 prev_cost 比较
    in_fixed_outline = false;  // 先假设还没有找到满足固定外框的可行解。后面如果找到，就会改成 true

    clock_t init_time = clock(); // 记录模拟退火开始时的 CPU 时间，用来算总运行时间
    clock_t time = init_time;    // 记录“上一段计时起点”。后面如果超时但还没找到可行解，会重置这个时间点。

    do
    {
        MT = 0;
        uphill = 0;
        reject = 0;

        // new----------------------------------------------
#if CURVE_MODE
        if (g_curve_mode)
        {
            T_Moves = 0;
            T_uphill = 0;
            T_reject = 0;
        }
#endif
        // new_end----------------------------------------------

        do
        {
            vector<HardBlock> hardblocks_temp(hardblocks); // 复制当前所有硬块的信息，作为临时备份。里面保存的是每个块当前的坐标、宽高、旋转状态等。
            vector<Node> btree_temp(btree);                // 复制当前 B*-tree 的结构，作为临时备份。里面保存的是每个节点的父子关系。
            int prev_root_block = root_block;              // 记录当前树的根节点编号。因为后面做 Swap 或 Move 时，根节点有可能变化，所以也要单独备份。

            // new--------------------------------
            // ---- 使用偏置选择模块对 ----
            bool use_bias = ((double)rand() / RAND_MAX) >= bias_explore_ratio;

            int M;
            int a, b;
            if (!use_bias)
            {
                // 完全随机选择操作
                M = rand() % 3;
                if (M == 0)
                {
                    a = rand() % num_hardblocks;
                    b = a; // 表示旋转
                }
                else if (M == 1)
                {
                    a = rand() % num_hardblocks;
                    do
                    {
                        b = rand() % num_hardblocks;
                    } while (a == b);
                }
                else if (M == 2)
                {
                    a = rand() % num_hardblocks;
                    do
                    {
                        b = rand() % num_hardblocks;
                    } while (a == b || btree[a].parent == b);
                }
                else
                {
                    cout << "[Error] Unspecified Move\n";
                    exit(1);
                }
            }
            else
            {
                // 偏置选择：先按固定概率选操作类型
                double op_rand = (double)rand() / RAND_MAX;
                if (op_rand < operation_probs[0])
                {
                    M = 0; // 旋转
                    a = rand() % num_hardblocks;
                    b = a;
                }
                else if (op_rand < operation_probs[0] + operation_probs[1])
                {
                    M = 1; // 交换
                    tie(a, b) = selector.selectPair(T);
                }
                else
                {
                    M = 2; // 移动
                    tie(a, b) = selector.selectPair(T);
                    // 移动前需要保证 b 不是 a 的父节点，你在实际执行时处理即可
                    if (btree[a].parent == b)
                    {
                        a = rand() % num_hardblocks;
                        do
                        {
                            b = rand() % num_hardblocks;
                        } while (a == b || btree[a].parent == b);
                    }
                }
            }
            //-----------------------------------

            // new--------------------------------
            // 执行扰动
            if (M == 0)
            {
                Rotate(a);
            }
            else if (M == 1)
            {
                Swap(a, b);
            }
            else
            { // M == 2
                // 防止移动时 b 是 a 的父节点（简单交换）
                Move(a, b);
            }
            //-----------------------------------

            // new----------------------------------------------
#if CURVE_MODE
            if (g_curve_mode)
            {
                Total_Moves++; // 实现总次数技计数
                T_Moves++;
            }
#endif
            // new_end----------------------------------------------

            MT++;                                               // 增量计数当前温度层的尝试次数。
            Cost cur_cost = CalculateCost();                    // 计算做完扰动后的当前解代价。
            double delta_cost = cur_cost.cost - prev_cost.cost; // 计算新解和当前基准解 prev_cost 之间的代价差；正值表示变差（更坏），负值表示变好（更优）。
            double random = ((double)rand()) / RAND_MAX;        // 生成一个 0 到 1 之间的随机浮点数，用于与 Metropolis 接受概率比较
            // new--------------------------------
            bool accepted = false; // 定义在循环内
            //-----------------------------------

            if (delta_cost <= 0 || random < exp(-delta_cost / T)) // 如果 delta_cost <= 0（变优或相等）或以概率 exp(-delta_cost / T) 接受变差解，则进入接受分支（Metropolis 准则）。
            {
                // new--------------------------------
                accepted = true;
                //-----------------------------------

                if (delta_cost > 0) // 若接受的是变差解（delta_cost > 0），则把 uphill++（记录当前温度下接受更差解的次数）。
                {
                    uphill++;

                    // new----------------------------------------------
#if CURVE_MODE
                    if (g_curve_mode)
                    {
                        T_uphill++;
                    }
#endif
                    // new_end----------------------------------------------
                }

                // feasible solution with minimum cost
                if (cur_cost.width <= W && cur_cost.height <= W) // 当 cur_cost.width <= W && cur_cost.height <= W 时视为落入固定外形（feasible）。
                {
                    if (in_fixed_outline)
                    {
                        if (cur_cost.cost < min_cost_fixed_outline.cost) // 如果已经有可行解（in_fixed_outline == true），且当前代价更小则更新可行解最优记录
                        {
                            min_cost_root_block_fixed_outline = root_block;
                            min_cost_fixed_outline = cur_cost;
                            min_cost_floorplan_fixed_outline = hardblocks;
                            min_cost_btree_fixed_outline = btree;
                        }
                    }
                    else
                    {
                        in_fixed_outline = true;                        // 标记可行解: in_fixed_outline = true; — 标记已经找到一个落入固定外形（宽高都 <= W）的可行解
                        min_cost_root_block_fixed_outline = root_block; // 记录当前解的根块编号，便于后续恢复/输出
                        min_cost_fixed_outline = cur_cost;              // 把当前计算得到的 Cost（宽、高、面积、线长、总代价等）保存为当前可行解的最优代价记录
                        min_cost_floorplan_fixed_outline = hardblocks;  // 复制并保存当前所有硬块的位置/尺寸/旋转状态，作为可行解的最优版图快照
                        min_cost_btree_fixed_outline = btree;           // 复制并保存当前的 B-树结构，作为可行解对应的树结构快照
                    }
                }

                // infeasible solution with minimum cost
                if (cur_cost.cost < min_cost.cost) // 若当前解的总代价更小，则更新“历史最优解”
                {
                    min_cost_root_block = root_block;
                    min_cost = cur_cost;
                    min_cost_floorplan = hardblocks;
                    min_cost_btree = btree;
                }

                prev_cost = cur_cost;
            }
            else
            {
                // new--------------------------------
                accepted = false;
#if CURVE_MODE
                if (g_curve_mode)
                {
                    T_reject++;
                }
#endif
                //-----------------------------------

                reject++;                     // 增加拒绝计数器（记录本次扰动被拒绝），用于后续停止/统计条件
                root_block = prev_root_block; // 把根节点恢复到扰动前的值（prev_root_block 在扰动前保存），以撤销可能的根变更
                if (M == 0)
                    hardblocks = hardblocks_temp; // 根据扰动类型恢复状态——当 M==0（旋转）只修改了 hardblocks，所以用 hardblocks_temp 回退
                else
                    btree = btree_temp; // 否则（swap 或 move）修改的是 btree，所以用 btree_temp 回退
            }
            // new--------------------------------
            // 非旋转操作就更新
            if (M != 0)
            {
                selector.update(a, b, delta_cost, T, accepted);
            }
            //-----------------------------------
        } while (uphill <= N && MT <= 2 * N); // 当拒绝次数小于k*num_blocks并且扰动次数小于2倍的k*num_blocks就继续，即拒绝够多或者扰动够多就结束该温度下的扰动

        T *= r; // 降低温度

        seconds = (clock() - time) / CLOCKS_PER_SEC;      // 计算自上一次重置 time 以来经过的秒数。
        runtime = (clock() - init_time) / CLOCKS_PER_SEC; // 计算从模拟退火开始 (init_time) 到现在的总运行秒数。
        if (seconds >= max_seconds && in_fixed_outline == false)
        { // 如果本阶段耗时超过 max_seconds 并且还没找到可行解，则执行超时处理：
            cout << "Overtime " << min_cost.width << " " << min_cost.height << '\n';
            seconds = 0; // 将 seconds 清零并把 time 设为当前时刻（重置阶段计时器）
            time = clock();
            T = T0; // 将温度 T 重置为初始温度 T0（相当于在超时后重新从高温开始搜索）
        }
        // 当且仅当两个条件都满足时继续：
        // 拒绝率 (float)reject/MT 小于等于 0.99（拒绝太多则停止当前退火过程），
        // 当前温度 T 不低于阈值 epsilon（温度过低也会停止）。
    } while ((float)reject / MT <= reject_rate && T >= epsilon);
    // 下面表明曾有过以阶段耗时和总运行时间为停止条件的替代退出策略。
    //  } while (seconds < max_seconds && runtime < TIME_LIMIT);

    if (in_fixed_outline)
    {
        // 循环结束后（比如在 return 0 前）
#ifdef DEBUG
        std::cout << '\n';
#endif
        cout << "Found feasible solution\n";
        cout << "Width:      " << min_cost_fixed_outline.width << '\n';
        cout << "Height:     " << min_cost_fixed_outline.height << '\n';
        cout << "Area:       " << min_cost_fixed_outline.area << '\n';
        cout << "Wirelength: " << min_cost_fixed_outline.wirelength << '\n';
        cout << "R:          " << min_cost_fixed_outline.R << '\n';
        cout << "Cost:       " << min_cost_fixed_outline.cost << '\n';
        cout << '\n';

        Verify(min_cost_floorplan_fixed_outline); // 验证硬块的布局之间有无重叠
    }
    else
    {
        // 循环结束后（比如在 return 0 前）
#ifdef DEBUG
        std::cout << '\n';
#endif
        cout << "Not Found feasible solution\n";
        cout << "Width:      " << min_cost.width << '\n';
        cout << "Height:     " << min_cost.height << '\n';
        cout << "Area:       " << min_cost.area << '\n';
        cout << "Wirelength: " << min_cost.wirelength << '\n';
        cout << "R:          " << min_cost.R << '\n';
        cout << "Cost:       " << min_cost.cost << '\n';
        cout << '\n';

        Verify(min_cost_floorplan);
    }
}

void FastSA(const FastSA_config &cfg)
{
#ifdef DEBUG
    ScopedTimer t("SimulatedAnnealing");
#endif

    // new----------------------------------------------
#if CURVE_MODE
    if (g_curve_mode)
    {
        Total_Moves = 0;
        T_Moves = 0;
        T_uphill = 0;
        T_reject = 0;
    }
#endif
    // new_end----------------------------------------------

    min_cost = CalculateCost();
    min_cost_floorplan = hardblocks;

    // ==================== FASTSA 参数 ====================
    const double P = cfg.P;                                        // 初始接受概率
    const double c = cfg.c;                                        // 论文推荐 c=100
    const int k = cfg.k;                                           // 论文推荐 k=7
    const int MAX_ITER = cfg.max_iter;                             // 最大迭代次数（安全上限）
    const int MAX_CONSECUTIVE_REJECT = cfg.max_consecutive_reject; // 连续拒绝阈值
    const double MIN_TEMP = cfg.min_temp;                          // 最低温度阈值
    double alpha = cfg.ewma_alpha;
    // ====================================================

    // -------------------- 预采样估算 Δavg --------------------
    vector<HardBlock> hardblocks_bak = hardblocks;
    vector<Node> btree_bak = btree;
    int root_block_bak = root_block;
    Cost min_cost_bak = min_cost;

    double total_uphill = 0.0;
    int uphill_count = 0;
    const int SAMPLE_SIZE = cfg.sample_size;

    for (int s = 0; s < SAMPLE_SIZE; ++s)
    {
        int M = rand() % 3;
        if (M == 0)
        {
            int node = rand() % num_hardblocks;
            Rotate(node);
        }
        else if (M == 1)
        {
            int node1 = rand() % num_hardblocks;
            int node2;
            do
            {
                node2 = rand() % num_hardblocks;
            } while (node2 == node1);
            Swap(node1, node2);
        }
        else
        {
            int node = rand() % num_hardblocks;
            int to_node;
            do
            {
                to_node = rand() % num_hardblocks;
            } while (to_node == node || btree[node].parent == to_node);
            Move(node, to_node);
        }
        Cost cur_cost = CalculateCost();
        double delta = cur_cost.cost - min_cost.cost;
        if (delta > 0)
        {
            total_uphill += delta;
            uphill_count++;
        }
        // 回滚
        hardblocks = hardblocks_bak;
        btree = btree_bak;
        root_block = root_block_bak;
        CalculateCost();
    }
    double delta_avg = (uphill_count > 0) ? (total_uphill / uphill_count) : 1.0;
    double T1 = delta_avg / log(P);
    // ----------------------------------------------------

    // 恢复原始状态
    hardblocks = hardblocks_bak;
    btree = btree_bak;
    root_block = root_block_bak;
    min_cost = min_cost_bak;
    CalculateCost();

    // -------------------- FASTSA 主循环 --------------------
    int iter = 0;                      // 全局迭代计数器
    double avg_delta_cost = delta_avg; // 平均代价变化（EWMA）
    // new-------------------------------------------------
    T = T1; // 当前温度
    // new_end----------------------------------------------
    Cost prev_cost = min_cost; // 当前接受解的成本
    in_fixed_outline = false;

    clock_t start_time = clock(); // 总开始时间（用于输出运行时间）
    clock_t time = start_time;    // 阶段计时起点（用于超时重启）
    const int max_seconds = (num_hardblocks / cfg.max_seconds_divisor) * (num_hardblocks / cfg.max_seconds_divisor);
    int seconds = 0;
    int consecutive_reject = 0; // 连续拒绝次数

    // 主循环：不设总时间限制，仅靠停止条件退出
    while (true)
    {
        // ---------- 超时重启检测 ----------
        seconds = (clock() - time) / CLOCKS_PER_SEC;
        if (seconds >= max_seconds && !in_fixed_outline)
        {
            cout << "Overtime " << min_cost.width << " " << min_cost.height << '\n';
            seconds = 0;
            time = clock();
            // 重置 FastSA 状态
            iter = 0;
            avg_delta_cost = delta_avg;
            T = T1;
            prev_cost = min_cost;
            consecutive_reject = 0;
        }

        // 执行一次迭代
        vector<HardBlock> hardblocks_temp = hardblocks;
        vector<Node> btree_temp = btree;
        int prev_root_block = root_block;

        int M = rand() % 3;
        if (M == 0)
        {
            int node = rand() % num_hardblocks;
            Rotate(node);
        }
        else if (M == 1)
        {
            int node1 = rand() % num_hardblocks;
            int node2;
            do
            {
                node2 = rand() % num_hardblocks;
            } while (node2 == node1);
            Swap(node1, node2);
        }
        else
        {
            int node = rand() % num_hardblocks;
            int to_node;
            do
            {
                to_node = rand() % num_hardblocks;
            } while (to_node == node || btree[node].parent == to_node);
            Move(node, to_node);
        }

        // new----------------------------------------------
#if CURVE_MODE
        if (g_curve_mode)
        {
            Total_Moves++;
            T_Moves++;
        }
#endif
        // new_end----------------------------------------------

        Cost cur_cost = CalculateCost();
        double delta_cost = cur_cost.cost - prev_cost.cost;

        // 更新平均代价变化
        avg_delta_cost = (1 - alpha) * avg_delta_cost + alpha * fabs(delta_cost);

        // FastSA 动态温度
        int n = iter + 1;
        if (n == 1)
        {
            T = T1;
        }
        else if (n <= k)
        {
            T = T1 * avg_delta_cost / (n * c);
        }
        else
        {
            T = T1 * avg_delta_cost / n;
        }
        if (T < MIN_TEMP)
            T = MIN_TEMP;

        double random = ((double)rand()) / RAND_MAX;
        if (delta_cost <= 0 || random < exp(-delta_cost / T))
        {
            // new----------------------------------------------
#if CURVE_MODE
            if (g_curve_mode && delta_cost > 0)
            {
                T_uphill++;
            }
#endif
            // new_end----------------------------------------------

            // 接受新解
            prev_cost = cur_cost;
            consecutive_reject = 0; // 重置连续拒绝计数

            // 固定外框可行解
            if (cur_cost.width <= W && cur_cost.height <= W)
            {
                if (in_fixed_outline)
                {
                    if (cur_cost.cost < min_cost_fixed_outline.cost)
                    {
                        min_cost_root_block_fixed_outline = root_block;
                        min_cost_fixed_outline = cur_cost;
                        min_cost_floorplan_fixed_outline = hardblocks;
                        min_cost_btree_fixed_outline = btree;
                    }
                }
                else
                {
                    in_fixed_outline = true;
                    min_cost_root_block_fixed_outline = root_block;
                    min_cost_fixed_outline = cur_cost;
                    min_cost_floorplan_fixed_outline = hardblocks;
                    min_cost_btree_fixed_outline = btree;
                }
            }

            // 全局最优解
            if (cur_cost.cost < min_cost.cost)
            {
                min_cost_root_block = root_block;
                min_cost = cur_cost;
                min_cost_floorplan = hardblocks;
                min_cost_btree = btree;
            }
        }
        else
        {
            // new----------------------------------------------
#if CURVE_MODE
            if (g_curve_mode)
            {
                T_reject++;
            }
#endif
            // new_end----------------------------------------------

            // 拒绝：回滚状态
            consecutive_reject++;
            root_block = prev_root_block;
            if (M == 0)
                hardblocks = hardblocks_temp;
            else
                btree = btree_temp;
            CalculateCost();
        }

        iter++;

        // ---------- 主动停止条件 ----------
        // 条件1：连续拒绝次数过多且温度很低（类似原算法的拒绝率很高且温度低）
        if (consecutive_reject >= MAX_CONSECUTIVE_REJECT && T <= MIN_TEMP)
        {
            break;
        }
        // 条件2：达到最大迭代次数（安全上限）
        if (iter >= MAX_ITER)
        {
            break;
        }
    }

    // 记录总运行时间
    double runtime = (double)(clock() - start_time) / CLOCKS_PER_SEC;
    cout << "Total runtime: " << runtime << " seconds" << endl;

    // -------------------- 输出结果（与原代码相同） --------------------
    if (in_fixed_outline)
    {
#ifdef DEBUG
        std::cout << '\n';
#endif
        cout << "Found feasible solution\n";
        cout << "Width:      " << min_cost_fixed_outline.width << '\n';
        cout << "Height:     " << min_cost_fixed_outline.height << '\n';
        cout << "Area:       " << min_cost_fixed_outline.area << '\n';
        cout << "Wirelength: " << min_cost_fixed_outline.wirelength << '\n';
        cout << "R:          " << min_cost_fixed_outline.R << '\n';
        cout << "Cost:       " << min_cost_fixed_outline.cost << '\n';
        cout << '\n';
        Verify(min_cost_floorplan_fixed_outline);
    }
    else
    {
#ifdef DEBUG
        std::cout << '\n';
#endif
        cout << "Not Found feasible solution\n";
        cout << "Width:      " << min_cost.width << '\n';
        cout << "Height:     " << min_cost.height << '\n';
        cout << "Area:       " << min_cost.area << '\n';
        cout << "Wirelength: " << min_cost.wirelength << '\n';
        cout << "R:          " << min_cost.R << '\n';
        cout << "Cost:       " << min_cost.cost << '\n';
        cout << '\n';
        Verify(min_cost_floorplan);
    }
}

// 这个函数的作用是把当前版图结果写到输出文件里，格式包括总线长和每个硬块的坐标、尺寸、是否旋转
void OutputFloorplan(string output_file, int wirelength, vector<HardBlock> &hb)
{
    ofstream file;          // 创建一个文件输出流对象。
    file.open(output_file); // 打开指定的输出文件，准备写入。

    file << "W:" << W << '\n';
    file << "Wirelength " << ":" << wirelength << '\n';
    file << "Blocks" << ":" << num_hardblocks << '\n';

    for (int i = 0; i < num_hardblocks; i++)
    {
        if (hb[i].rotate)
            file << "sb" << i << " " << hb[i].x << " " << hb[i].y << " " << hb[i].height << " " << hb[i].width << " 1\n";
        else
            file << "sb" << i << " " << hb[i].x << " " << hb[i].y << " " << hb[i].width << " " << hb[i].height << " 0\n";
    }

    file.close();
}

unsigned int GetRandomSeed()
{
    if (num_hardblocks == 100)
    {
        if (white_space_ratio == 0.1)
            return 1542894266;
        else if (white_space_ratio == 0.15)
            return 1542894588;
    }
    else if (num_hardblocks == 200)
    {
        if (white_space_ratio == 0.1)
            return 1542892927;
        else if (white_space_ratio == 0.15)
            return 1542892927;
    }
    else if (num_hardblocks == 300)
    {
        if (white_space_ratio == 0.1)
            return 1542959801;
        else if (white_space_ratio == 0.15)
            return 1542955417;
    }

    return time(NULL);
}

int main(int argc, char **argv)
{
    // 默认算法模式
    int algo_mode = 0; // 0: 原始, 1: GMS, ...
    bool curve_mode = false;

    // 1. 扫描所有参数，提取 --algo 或 -a
    vector<string> args; // 存储非选项参数
    for (int i = 1; i < argc; i++)
    {
        if (strcmp(argv[i], "--algo") == 0 || strcmp(argv[i], "-a") == 0)
        {
            if (i + 1 < argc)
            {
                algo_mode = atoi(argv[i + 1]);
                i++; // 跳过值
            }
            else
            {
                cerr << "错误: --algo 选项需要指定一个整数参数 (0, 1, 2, ...)" << endl;
                return 1;
            }
        }
        else if (strcmp(argv[i], "--curve") == 0 || strcmp(argv[i], "-c") == 0)
        {
            curve_mode = true;
            // 如果希望带参数，如 --curve=1，可另写解析逻辑，这里简单开关
        }
        else
        {
            args.push_back(argv[i]);
        }
    }

    // 设置全局曲线模式
    g_curve_mode = curve_mode;

    // 2. 检查剩余参数数量 (至少5个: hardblocks, nets, pl, floorplan, ratio)
    if (args.size() < 5)
    {
        cout << "[Usage]\n";
        cout << "    ./hw3 [--algo N] <.hardblocks> <.nets> <.pl> <.floorplan> <white_space_ratio> [seed]\n";
        return 1;
    }

    // 3. 按顺序读取固定参数
    string hardblocks_file = args[0];
    string nets_file = args[1];
    string terminals_file = args[2];
    string floorplan_file = args[3];
    white_space_ratio = atof(args[4].c_str());

    unsigned int seed;
    if (args.size() >= 6)
    {
        seed = static_cast<unsigned int>(atoi(args[5].c_str()));
    }
    else
    {
        seed = GetRandomSeed();
    }

    // 4. 显示选择的算法模式（可选）
    cout << "Algorithm mode: " << algo_mode << endl;

    ReadHardblocksFile(hardblocks_file);
    ReadNetsFile(nets_file);
    ReadTerminalsFile(terminals_file);

    srand(seed);
    cout << "Random seed: " << seed << "\n\n";

    BuildInitBtree(); // 随机化建立树
    // InitBtree();

    // 5. 根据模式调用不同算法
    // 注意：读取文件、构建初始解等公共部分应该提前完成，这里只调用求解函数
    // 假设读取数据的函数已经调用，或者已经全局可用
    switch (algo_mode)
    {
    case 1: // GMS
    {
        GMS_config gms_cfg;
        SimulatedAnnealing_GMS(gms_cfg);
        break;
    }
    case 2: // FastSA
    {
        FastSA_config fastsa_cfg;
        FastSA(fastsa_cfg);
        break;
    }
    default: // 默认算法
    {
        SA_config sa_cfg;
        SimulatedAnnealing(sa_cfg);
        break;
    }
    }

    // 输出文件
    if (in_fixed_outline)
        OutputFloorplan(floorplan_file, min_cost_fixed_outline.wirelength, min_cost_floorplan_fixed_outline);
    else
        OutputFloorplan(floorplan_file, min_cost.wirelength, min_cost_floorplan);

    return 0;
}
