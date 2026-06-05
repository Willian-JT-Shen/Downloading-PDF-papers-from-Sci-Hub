"""
将命令行 Python 脚本包装成图形用户界面（GUI）的问题，在软件开发中称为“脚本前端化”或“CLI 工具 GUI 化”

问题定位：
一个 文件选择 / 上传 功能（指定 .bib 文件）；
一个 目录选择 功能（指定 PDF 下载保存的文件夹）；
一个 运行按钮 触发你已经写好的 Python 导出逻辑；

使用 Gooey 工具

打包成独立软件的命令（将以下命令复制到终端）
    pip install pyinstaller
    # pyinstaller --onefile --noconsole front_end_scripting_gooey.py
    # pyinstaller --onefile --windowed --icon=logo.ico front_end_scripting_gooey.py  # 图标用 logo.ico
    pyinstaller --onefile --windowed --icon=logo.ico `
        --add-data "chromedriver-win64;chromedriver-win64" `
        --add-data "chrome-win64;chrome-win64" `
        --collect-all selenium `
        --collect-all pandas `
        --collect-all tqdm `
        --collect-all bibtexparser `
        --collect-all requests `
        front_end_scripting_gooey.py
    # 结果生成在 dist 文件夹中

用 Inno Setup，将 .exe 程序打包成专业安装包，包括安装向导、桌面快捷方式、开始菜单文件夹、卸载支持等
    官网：https://jrsoftware.org/isinfo.php

"""
import argparse
import os
from sci_hub_export import Article_export as ae

import ctypes
import sys
if sys.platform == 'win32':
    # 告诉系统本程序自己处理 DPI 缩放
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 1 = 系统 DPI 感知
    except AttributeError:
        # 旧版 Windows 兼容
        ctypes.windll.user32.SetProcessDPIAware()
from gooey import Gooey, GooeyParser

@Gooey(
    program_name="BibTeX PDF 导出工具",
    default_size=(950, 800),
    required_cols=1,          # 参数标签和控件上下排列
    optional_cols=1,
    font=('Segoe UI', 10),        # Windows 清晰字体，字号 10
)
def main():
    parser = GooeyParser(description="选择一个 .bib 文件并指定保存文件夹")
    parser.add_argument("bibfile",
                        metavar="BibTeX 文件",
                        widget="FileChooser",
                        help="选择你要处理的 .bib 文件",
                        gooey_options={
                            'wildcard': "BibTeX files (*.bib)|*.bib",
                            'message': "请选择一个 .bib 文件"
                        }
                        )
    parser.add_argument("output_dir",
                        metavar="保存目录",
                        widget="DirChooser",
                        help="选择 PDF 保存的目标文件夹",
                        )
    args = parser.parse_args()

    # 调用核心功能
    export_class = ae(BIB_FILE=args.bibfile, SAVE_DIR=args.output_dir)
    export_class.run()

if __name__ == '__main__':
    main()









