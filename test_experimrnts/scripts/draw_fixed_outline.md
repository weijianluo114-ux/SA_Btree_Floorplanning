您需要绘制一个布局规划的矩形图。下面提供完整的 Python 脚本，它可以读取您描述的格式文件，并使用 `matplotlib` 绘制所有矩形块，同时支持标注块名称。

## 使用方法

1. **安装依赖**（仅需 `matplotlib`）：

   ```bash
   pip install matplotlib
   ```

   这里可以直接按下面这样安装
   安装依赖：在部署项目时，使用下面的命令安装：

   ```bash
   conda create SA_Btree python=3.11 -y
   pip install -r requirements.txt
   ```
2. **准备布局文件**，例如 `result.txt`，内容如下（示例）：

   ```
   W:444
   Wirelength :235485
   Blocks:5
   sb0 212 299 43 33 1
   sb1 330 67 65 37 0
   sb2 209 342 53 34 0
   sb3 80 0 37 67 0
   sb4 171 275 29 19 1
   ```
3. **运行脚本**：

   ```bash
   cd scripts
   python draw_fixed_outline.py --input_file ../output/test_100blocks_ratio_0_15_total_10/run6_2026-06-04_20:42:11.floorplan -o ../results/floor_plan_figures/floorplan_original_run6.png
   ```

   如果不指定 `-o`，则会弹出窗口显示。
4. **可选参数**：

   - `--no_labels`：不在矩形中央显示块名称。
   - `--dpi 300`：提高输出图片分辨率。

## 格式说明

- 第一行 `W:444` 是可选的，用于指定整个芯片的宽度（画布 x 轴上限）。如果没有这一行，脚本会自动取所有块 `x+width` 的最大值作为宽度。
- 第二行 `Wirelength :...` 会被自动跳过。
- 第三行 `Blocks:100` 用于校验，但不强制。
- 每一行数据必须包含 6 个字段：`名称 x y 参数3 参数4 方向`。
  - 方向 `1`：`(height, width) = (参数3, 参数4)`
  - 方向 `0`：`(width, height) = (参数3, 参数4)`

## 输出示例

脚本会生成一张带有网格和矩形块的图片，每个矩形中心标注块名称，坐标轴等比例显示。

如果您需要调整颜色、透明度、字体大小等，可以修改脚本中的对应参数（如 `facecolor='lightblue'`、`fontsize=8`）。
