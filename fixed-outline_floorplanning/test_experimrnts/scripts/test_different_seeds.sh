#!/bin/bash

# ================== 配置 ==================
# 可执行文件（从 bin/ 向上一层即是 test_experiments/，hw3_dbg 编译后默认在这里）
EXEC="../bin/hw3_dbg"

# 测试数据文件（testcase 与 test_experiments 平级，所以从 bin/ 出发需要 ../../testcase/）
HARDBLOCKS="../../testcase/n100.hardblocks"
NETS="../../testcase/n100.nets"
TERMINALS="../../testcase/n100.pl"

WHITE_SPACE_RATIO=0.1
NUM_RUNS=20

# 输出 floorplan 的前缀（output 与 test_experiments 平级）
FLOORPLAN_PREFIX="../../output/test_${NUM_RUNS}"

# 日志文件和种子文件存放在脚本所在目录（bin/）
LOG_FILE="../log/running_results_$(date +%Y-%m-%d_%H:%M:%S).txt"
SEED_FILE="../seeds/seeds_${NUM_RUNS}_$(date +%Y-%m-%d_%H:%M:%S).txt"

# 确保 output 目录存在
mkdir -p ../../output/test_${NUM_RUNS}

# ================== 生成种子列表 ==================
echo "生成 $NUM_RUNS 个随机种子..."
> "$SEED_FILE"  # 清空或创建
for i in $(seq 1 $NUM_RUNS); do
    # 组合两个 $RANDOM 以获得更大范围的种子
    seed=$(( ($RANDOM << 15) + $RANDOM ))
    echo $seed >> "$SEED_FILE"
done

# ================== 批量执行 ==================
echo "开始批量测试，结果将保存到 $LOG_FILE"
echo "==============================================" > "$LOG_FILE"
echo "Batch floorplanning experiment" >> "$LOG_FILE"
echo "Hardblocks: $HARDBLOCKS" >> "$LOG_FILE"
echo "Nets:       $NETS" >> "$LOG_FILE"
echo "Terminals:  $TERMINALS" >> "$LOG_FILE"
echo "Ratio:      $WHITE_SPACE_RATIO" >> "$LOG_FILE"
echo "Runs:       $NUM_RUNS" >> "$LOG_FILE"
echo "Start time: $(date)" >> "$LOG_FILE"
echo "==============================================" >> "$LOG_FILE"

run=1
while read seed; do
    echo "============================================" >> "$LOG_FILE"
    echo " Run $run / $NUM_RUNS  (seed = $seed)" >> "$LOG_FILE"
    echo "============================================" >> "$LOG_FILE"

    # 每次运行使用独立的 floorplan 文件，避免覆盖
    floorplan_file="${FLOORPLAN_PREFIX}/run${run}.floorplan"

    # 执行程序，标准输出和错误都追加到日志
    $EXEC "$HARDBLOCKS" "$NETS" "$TERMINALS" "$floorplan_file" "$WHITE_SPACE_RATIO" "$seed" >> "$LOG_FILE" 2>&1

    # 在终端显示进度
    echo "[$run/$NUM_RUNS] seed=$seed done."
    ((run++))
done < "$SEED_FILE"

echo "============================================" >> "$LOG_FILE"
echo "All tests finished at $(date)" >> "$LOG_FILE"
echo "Log saved to $LOG_FILE"
echo "Seeds saved to $SEED_FILE"