# 键鼠操控工具箱（MachineControl）

Windows 桌面自动化合集，四个工具收进一个托盘面板：

| 模块 | 入口 | 功能 |
|---|---|---|
| 🎥 键鼠录制/回放 | `recorder.py` | SendInput 级录制回放，全局热键 F9/F8 控制 |
| ⏱ 脚本控制台 | `console.py` | 事件表格逐行编辑、键鼠图示可视化、定时执行 |
| 🔍 屏幕文字侦查 | `ocr_monitor.py` | Tesseract OCR 关键词触发规则 + YOLO 图形检测（子进程隔离） |
| 📁 文件管理 | `file_manager.py` | 配套文件整理 |

统一入口 `main.py`：常驻系统托盘（F10 显隐），一次 DPI 感知、一个主循环、一份日志。

## 快速开始

```bat
python -m pip install -r requirements.txt
python main.py
```

另需系统级安装 [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/wiki)（含 chi_sim 中文包）。
图形监察（YOLO）为可选功能，跑在独立 conda 环境子进程，见 `requirements.txt` 底部说明。

## 文档

- [图形监察-使用说明.md](图形监察-使用说明.md) —— YOLO 环境搭建与权重选择
- [键鼠可视化-说明.md](键鼠可视化-说明.md) —— 脚本控制台的事件图示
- [数据存放位置-必读.md](数据存放位置-必读.md) —— 录制脚本存 `%LOCALAPPDATA%`，重打包不丢

## 注意

- 录制脚本等用户数据在 `%LOCALAPPDATA%\机器操控工具箱\`，不在本目录；备份请用界面「导出选中」。
- 打包发布走 PyInstaller（`build/`、`dist/` 已 gitignore）。
