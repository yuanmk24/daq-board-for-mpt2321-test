# FPGA 引脚文本处理脚本使用说明

脚本: `modify_fpga_txt.py`

## 目标
读取 Xilinx FPGA 封装引脚文本文件（例如 `xc7k325tfbg676pkg.txt`），为每一行的 PIN NAME 自动追加对应 PIN 号后缀，或生成精简格式仅保留三列：`Pin` / `Pin_Name`（追加后缀） / `Bank`。便于后续原理图/约束文件自动化处理。

## 功能概述
1. 标准模式（默认）：
   - 保留原文件的首行描述与标题行。
   - 为每条符合格式的引脚行的第二列 PIN NAME 追加 `_<PIN>` 后缀（若尚未追加）。
   - 其余列原样保留，列之间用单个空格连接。
2. 精简模式（`--minimal`）：
   - 去除文件首行设备描述与原始标题行。
   - 输出统一标题行：`Pin Pin_Name Bank`，若加 `--direction` 则为 `Pin Pin_Name Bank Direction`。
   - 仅保留引脚号、处理后的 PIN 名以及 Bank 列，可选自动推断方向。
   - 过滤无关行（空行、统计行、无法匹配引脚号格式行）。

## 引脚号与匹配规则
引脚号匹配正则: `^[A-Z]{1,2}[0-9]{1,2}$` （示例：`R11`, `AA25`, `B6`）。只有匹配该格式的行才会处理 PIN NAME 后缀。

## 输出文件策略
默认输出到与输入同目录下：`<原文件名>_modified.txt`。
可使用：
- `-o <文件路径>` 指定输出文件。
- `--inplace` 原地覆盖输入文件（谨慎使用）。
- `--minimal` 切换为精简模式；此时仍可配合 `-o` 或 `--inplace`。

## 命令行参数
| 参数 | 说明 |
|------|------|
| `input` | 必填，原始引脚文本文件路径 |
| `-o, --output` | 可选，指定输出文件路径 |
| `--inplace` | 原地覆盖输入文件（优先于 `--output`） |
| `--encoding` | 指定文件编码（默认 `utf-8`） |
| `--minimal` | 精简模式，仅输出三列 (可与 --direction 配合) |
| `--direction` | 与 --minimal 配合，增加 Direction 列 (POWER / CONFIG / IO / UNKNOWN) |

## 使用示例（Windows PowerShell）
```powershell
# 1. 标准模式，生成默认命名文件
python .\modify_fpga_txt.py .\xc7k325tfbg676pkg.txt

# 2. 标准模式，指定输出文件
python .\modify_fpga_txt.py .\xc7k325tfbg676pkg.txt -o .\xc7k325tfbg676pkg_modified.txt

# 3. 标准模式，原地覆盖
python .\modify_fpga_txt.py .\xc7k325tfbg676pkg.txt --inplace

# 4. 精简模式，生成三列输出
python .\modify_fpga_txt.py .\xc7k325tfbg676pkg.txt --minimal -o .\xc7k325tfbg676pkg_minimal.txt

# 5. 指定编码（如果原文件不是 UTF-8）
python .\modify_fpga_txt.py .\xc7k325tfbg676pkg.txt --encoding gbk --minimal -o .\pins_minimal.txt
```

## 输出示例（精简模式）
```
Pin Pin_Name Bank
R11 DXN_0_R11 0
M12 VCCADC_0_M12 0
## 输出示例（精简 + 方向）
```
Pin Pin_Name Bank Direction
R11 DXN_0_R11 0 IO
M12 VCCADC_0_M12 0 POWER
M11 GNDADC_0_M11 0 POWER
R12 DXP_0_R12 0 IO
...
```

## Direction 推断规则
当前是一个简易启发式分类：
- 包含任意电源/地关键字：`VCC`, `VCCAUX`, `VCCO`, `GND`, `VREF`, `VCCADC`, `GNDADC`, `VCCBATT` => `POWER`
- 包含配置/JTAG相关：`PROGRAM`, `DONE`, `INIT_B`, `TCK`, `TMS`, `TDI`, `TDO`, `CCLK`, `CFGBVS` => `CONFIG`
- 常规 IO 前缀或差分：以/包含 `IO_`, `IO_L`, `DXP`, `DXN`, `VP_`, `VN_`, `M0_`, `M1_`, `M2_` 或含有 `P_`/`N_`（且非电源/地） => `IO`
- 未匹配 => `UNKNOWN`

你可以根据需要进一步细化为 IN / OUT / BIDIR，或添加特殊前缀。
...
AA25 IO_L7P_T1_12_AA25 12
```

## 常见问题与说明
1. 报警告 `SyntaxWarning: invalid escape sequence`：已通过在脚本开头使用原始字符串字面量处理，不影响功能，可忽略。
2. 如果某些电源/地管脚（如 `VCCO_14`）也需要保留，请确认它们是否符合引脚号格式；若符合，会被处理并保留。
3. 若不希望追加后缀，可后续扩展 `--no-suffix` 功能（当前未实现）。
4. Bank 列定位为原文件中的第 4 列（标题行中 `Bank` 所在列）。如果源文件格式变化，需同步调整脚本逻辑。

## 扩展规划（可选）
- `--csv` 导出为 CSV 格式便于 Excel 导入。
- `--filter-bank <list>` 只保留指定 Bank（支持逗号分隔）。
- `--no-suffix` 选项禁用后缀追加。
- `--align` 输出对齐列宽，提升可读性。

如需上述扩展或适配其他器件的不同文本格式，欢迎继续提出需求。

## 许可证
此脚本为内部使用示例，未附加特定开源许可证；如需对外发布请自行添加合适的 LICENSE。
