r"""FPGA pin name post-processor.

读取指定的 Xilinx FPGA 封装引脚文本文件 (例如 `xc7k325tfbg676pkg.txt`)，
将每一行的第二列 PIN NAME 后面追加后缀 `_<PIN_NUMBER>`，其中 PIN_NUMBER 为该行第一列的引脚号（例如 R11）。

特性 / 规则:
1. 跳过首行标题 (以 'Pin' 开头且包含 'Pin Name').
2. 跳过纯空行或全是空白的行。
3. 如果 PIN NAME 已经以 `_<PIN_NUMBER>` 结尾，则不重复追加。
4. 保持其它列内容不变，使用单个空格重新拼接列，减少对齐复杂度。
5. 默认输出到同目录下 `<原文件名>_modified.txt`，可用 --inplace 原地覆盖。
6. 可用 --encoding 指定文件编码 (默认 utf-8)。

用法示例 (PowerShell):
  python .\modify_fpga_txt.py .\xc7k325tfbg676pkg.txt
  python .\modify_fpga_txt.py .\xc7k325tfbg676pkg.txt --inplace
  python .\modify_fpga_txt.py .\xc7k325tfbg676pkg.txt -o .\out.txt

Author: Auto-generated
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import List


HEADER_PIN_COL_NAME = "Pin"
HEADER_PINNAME_COL_NAME = "Pin Name"
PIN_NUMBER_PATTERN = re.compile(r"^[A-Z]{1,2}[0-9]{1,2}$")  # 例如 R11, AA25 等

def parse_columns(line: str) -> List[str]:
	"""用正则按任意数量空白分割一行，返回列列表。保留原始行用于输出时参考。"""
	raw = line.rstrip("\r\n")
	if not raw.strip():
		return []
	return re.split(r"\s+", raw.strip())


def need_skip_as_header(columns: List[str]) -> bool:
	"""判断是否是标题行 (列1为 Pin 且列2为 Pin Name)。"""
	if len(columns) < 2:
		return False
	return columns[0] == HEADER_PIN_COL_NAME and columns[1] == HEADER_PINNAME_COL_NAME


def process_pin_line(columns: List[str]) -> List[str]:
	"""对解析出的列进行 PIN NAME 后缀追加逻辑 (仅当第一列符合引脚号格式)。"""
	if len(columns) < 2:
		return columns
	pin_number = columns[0]
	if not PIN_NUMBER_PATTERN.match(pin_number):
		return columns
	pin_name = columns[1]
	suffix = f"_{pin_number}"  # 要追加的后缀
	if pin_name.endswith(suffix):
		return columns
	columns[1] = pin_name + suffix
	return columns


def process_file(input_path: pathlib.Path, output_path: pathlib.Path, encoding: str) -> int:
	"""处理整个文件，返回修改的行数。"""
	modified_count = 0
	with input_path.open("r", encoding=encoding, errors="ignore") as f_in, output_path.open("w", encoding=encoding) as f_out:
		first_line = True
		for raw_line in f_in:
			if first_line:
				# 原样保留第一行 (设备与时间信息)
				f_out.write(raw_line.rstrip("\r\n") + "\n")
				first_line = False
				continue
			columns = parse_columns(raw_line)
			if not columns:
				f_out.write("\n")
				continue
			if need_skip_as_header(columns):
				# 原样保留标题行
				f_out.write(raw_line.rstrip("\r\n") + "\n")
				continue
			before = columns[1] if len(columns) > 1 else ""
			columns = process_pin_line(columns)
			after = columns[1] if len(columns) > 1 else ""
			if before != after:
				modified_count += 1
			f_out.write(" ".join(columns) + "\n")
	return modified_count


def infer_direction(original_pin_name: str) -> str:
	"""根据名称模式推断方向 (粗分类)。返回值: POWER / CONFIG / IO / UNKNOWN。"""
	name_u = original_pin_name.upper()
	power_tokens = ["VCC", "VCCAUX", "VCCO", "GND", "VREF", "VCCADC", "GNDADC", "VCCBATT"]
	for tk in power_tokens:
		if tk in name_u:
			return "POWER"
	config_tokens = ["PROGRAM", "DONE", "INIT_B", "TCK", "TMS", "TDI", "TDO", "CCLK", "CFGBVS"]
	for tk in config_tokens:
		if tk in name_u:
			return "CONFIG"
	io_prefixes = ["IO_", "IO_L", "DXP", "DXN", "VP_", "VN_", "M0_", "M1_", "M2_"]
	for pre in io_prefixes:
		if name_u.startswith(pre) or pre in name_u:
			return "IO"
	if ("P_" in name_u or "N_" in name_u) and "VCC" not in name_u and "GND" not in name_u:
		return "IO"
	return "UNKNOWN"


def process_file_minimal(input_path: pathlib.Path, output_path: pathlib.Path, encoding: str, add_direction: bool = False) -> int:
	"""只保留 PIN, PIN_NAME(带后缀), Bank (可选 Direction) 列。过滤第一行描述、标题行、总计行、空行以及不匹配引脚号格式的行。"""
	modified_count = 0
	with input_path.open("r", encoding=encoding, errors="ignore") as f_in, output_path.open("w", encoding=encoding) as f_out:
		first_line = True
		if add_direction:
			f_out.write("Pin Pin_Name Bank Direction\n")
		else:
			f_out.write("Pin Pin_Name Bank\n")
		for raw_line in f_in:
			if first_line:
				first_line = False
				continue  # 丢弃首行描述
			stripped = raw_line.strip()
			if not stripped:
				continue
			if stripped.lower().startswith("total number of pins"):
				continue
			columns = parse_columns(raw_line)
			if need_skip_as_header(columns):
				continue
			if len(columns) < 5:
				continue
			pin_number = columns[0]
			if not PIN_NUMBER_PATTERN.match(pin_number):
				continue
			bank = columns[3]
			before_name = columns[1]
			processed_cols = process_pin_line(columns.copy())
			after_name = processed_cols[1]
			if before_name != after_name:
				modified_count += 1
			if add_direction:
				dir_val = infer_direction(before_name)
				f_out.write(f"{pin_number} {after_name} {bank} {dir_val}\n")
			else:
				f_out.write(f"{pin_number} {after_name} {bank}\n")
	return modified_count


def build_arg_parser() -> argparse.ArgumentParser:
	p = argparse.ArgumentParser(description="Append _<PIN> suffix to FPGA pin names in a text file.")
	p.add_argument("input", type=pathlib.Path, help="输入的原始引脚文件路径")
	p.add_argument("-o", "--output", type=pathlib.Path, help="输出文件路径 (缺省: <input>_modified.txt)")
	p.add_argument("--inplace", action="store_true", help="原地覆盖输入文件 (优先于 --output)")
	p.add_argument("--encoding", default="utf-8", help="文件编码, 默认 utf-8")
	p.add_argument("--minimal", action="store_true", help="仅输出三列: Pin Pin_Name Bank (过滤非PIN行) 可配合 --direction 增加方向列")
	p.add_argument("--direction", action="store_true", help="(与 --minimal 配合) 增加 Direction 列，根据 PIN NAME 推断: POWER/CONFIG/IO/UNKNOWN")
	return p


def main(argv: List[str]) -> int:
	parser = build_arg_parser()
	args = parser.parse_args(argv)
	input_path: pathlib.Path = args.input
	if not input_path.exists():
		print(f"[错误] 输入文件不存在: {input_path}", file=sys.stderr)
		return 2
	if args.inplace:
		output_path = input_path
	else:
		output_path = args.output or input_path.with_name(input_path.stem + "_modified.txt")

	if args.minimal:
		modified = process_file_minimal(input_path, output_path, args.encoding, add_direction=args.direction)
		print(f"[minimal{' +direction' if args.direction else ''}] 处理完成: 修改 {modified} 行. 输出文件: {output_path}")
	else:
		modified = process_file(input_path, output_path, args.encoding)
		print(f"处理完成: 修改 {modified} 行. 输出文件: {output_path}")
	return 0


if __name__ == "__main__":  # pragma: no cover
	raise SystemExit(main(sys.argv[1:]))

