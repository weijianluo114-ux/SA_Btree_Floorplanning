以下 Python 脚本实现了与给定 Bash 脚本相同的功能，并增加了表格记录与统计分析能力。
脚本支持通过 `argparse` 传递所有关键参数，自动执行编译、种子生成、批量运行、结果提取与统计汇总。

---

## 主要功能说明

1. **自动编译**通过 `--skip_make` 控制是否执行 `make -f Makefile.debug`，默认开启编译。
2. **灵活的参数传递**所有 Bash 脚本中的参数（可执行文件路径、测试数据、空白比例、运行次数、输出目录、日志文件、种子文件等）均可通过命令行指定，并提供合理默认值。
3. **种子生成**采用与 Bash 相同的 `((RANDOM<<15)+RANDOM)` 方法生成随机种子，范围 0 ~ 2^30-1，并保存到种子文件。
4. **批量运行与输出解析**

   - 为每次运行创建独立的 `.floorplan` 文件（位于自动创建的输出目录下）。
   - 使用正则表达式提取 `Width`、`Height`、`Area`、`Wirelength`、`R`、`Cost` 指标。
   - 完整的原始输出（stdout+stderr）存入日志文件，便于排查问题。
5. **结果表格与统计分析**

   - 所有提取的指标写入 CSV 文件，每行对应一次运行。
   - 自动计算每个指标的 **平均值** 和 **方差**（忽略缺失值）。
   - 统计信息同时打印到终端并追加到日志文件末尾。
6. **路径处理**
   所有路径均相对于脚本所在目录（`根目录`）自动解析为绝对路径，确保与原始 Bash 脚本的目录结构兼容。

---

## 使用示例

```bash
# 进入根目录，运行脚本（假设脚本名为 test_scripts.py）
python test_scripts.py --num_runs 2 --white_space_ratio 0.15

#若要快速进行n次（最多10次）曲线记录实验，则运行以下脚本
python test_scripts.py --num_runs 10 --white_space_ratio 0.15 --record_curve

# 自定义所有参数
python test_scripts.py \
    --executable ../bin/hw3_dbg \
    --hardblocks ./testcase/n200.hardblocks \
    --nets ./testcase/n200.nets \
    --terminals ./testcase/n200.pl \
    --white_space_ratio 0.2 \
    --num_runs 50 \
    --output_dir ./output/my_exp \
    --log_file ./log/my_exp.log \
    --seed_file ./seeds/my_seeds.txt \
    --results_csv ./results/my_results.csv \
    --record_curve
```

---

## 注意事项

- 脚本假定您的目录结构与 Bash 脚本一致：`test_experiments/` 下放置本脚本，`./bin/hw3_dbg` 为编译产物，`./testcase/` 存放测试数据。
- 若需跳过编译，添加 `--skip_make` 参数。
- 所有输出目录（`output/`、`log/`、`seeds/`、`results/`）会自动创建。
- 缺失指标（如程序未输出某行）在 CSV 中为空，统计时自动忽略。
- 若需进行n次的曲线脚本实验请加上 `--record_curve`参数
- 曲线脚本实验的实验上限次数为10，以防止输出过大
