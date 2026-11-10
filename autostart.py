"""开机自启动：读写当前用户注册表的 Run 项（HKCU\\...\\CurrentVersion\\Run）。

【为什么从「启动文件夹的 .lnk」改成「注册表 Run」】
实测结论（2026/11/04）：
  - 用启动文件夹方式，本机登录后**程序根本没被拉起**——app.log 最后一行
    02:04:01，而这次开机时间是 13:01:03，登录 7 分钟里日志一行都没多。
  - 根因是那个 exe 带有 AppCompat 兼容性标记 `~ RUNASADMIN`
    （HKCU\\...\\AppCompatFlags\\Layers），等于「每次启动都要求提权」，
    而登录阶段不允许提权，于是被 Windows 静默跳过、不报错也不弹窗。
  - 同一台机器上 `D:\\水印歌词` 用的是注册表 HKCU Run 项，能正常自启。
所以改用 Run 项，和已经验证可用的「水印歌词」保持同一套机制。

配套要求：exe 清单必须是 asInvoker、且不带 RUNASADMIN 兼容标记，
让它在登录阶段以普通权限正常起来，再由主程序 _self_elevate() 自己提权重启。
（清单写 requireAdministrator、或加 RUNASADMIN，都会重现「登录时不启动」。）

目标永远是**当前正在运行的 exe**；源码运行时则指向 `pythonw.exe main.py`，
这样开发时开启自启动也不会指向一个不存在的 exe。
"""
from __future__ import annotations

import os
import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "MachineCtrlToolbox"

# 老版本用的启动文件夹快捷方式名。开启/关闭时会顺手清掉，避免两套机制并存
# 导致登录时被拉起两次（虽然单实例锁会兜住，但会闪一下窗口）。
LEGACY_SHORTCUT_NAME = "机器操控工具箱.lnk"


def _startup_dir() -> str:
    """当前用户的启动文件夹路径（只用于清理旧版本留下的快捷方式）。"""
    appdata = os.environ.get("APPDATA") or os.path.expanduser(r"~\AppData\Roaming")
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu",
                        "Programs", "Startup")


def legacy_shortcut_path() -> str:
    return os.path.join(_startup_dir(), LEGACY_SHORTCUT_NAME)


def _command() -> str:
    """返回写进 Run 项的命令行。

    打包版 → 指向 exe 自己；
    源码版 → 用 pythonw.exe（无控制台窗口）跑 main.py。
    路径统一加引号，防止中文/空格路径被拆开。
    """
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}"'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.isfile(pyw):
        pyw = sys.executable        # 没有 pythonw 就退回 python（会带控制台）
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return f'"{pyw}" "{script}"'


def is_enabled() -> bool:
    """Run 项里是否有我们的命令。"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            value, _ = winreg.QueryValueEx(k, VALUE_NAME)
            return bool(value)
    except OSError:
        return False


def current_command() -> str:
    """读出当前登记的命令（没有则空串）。"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            value, _ = winreg.QueryValueEx(k, VALUE_NAME)
            return str(value)
    except OSError:
        return ""


def _clear_legacy_shortcut() -> bool:
    """删掉旧版本写进启动文件夹的快捷方式。返回是否真的删了东西。"""
    link = legacy_shortcut_path()
    if os.path.isfile(link):
        try:
            os.remove(link)
            return True
        except OSError:
            pass
    return False


def enable() -> str:
    """写入 Run 项。失败抛异常，由调用方提示。"""
    import winreg

    cmd = _command()
    # 打包版要确认目标 exe 真的在，否则写进去也没意义
    if getattr(sys, "frozen", False) and not os.path.isfile(sys.executable):
        raise FileNotFoundError(f"启动目标不存在：{sys.executable}")

    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as k:
            winreg.SetValueEx(k, VALUE_NAME, 0, winreg.REG_SZ, cmd)
    except OSError as exc:
        raise OSError(f"写入注册表 Run 项失败：{exc}") from exc

    # 回读校验：SetValueEx 不抛异常不等于写进去了
    if current_command() != cmd:
        raise OSError(f"Run 项回读不一致：期望 {cmd!r}，实际 {current_command()!r}")

    removed = _clear_legacy_shortcut()
    tail = "（已顺带清理旧的启动文件夹快捷方式）" if removed else ""
    return f"已开启开机自启动 → HKCU\\{RUN_KEY}\\{VALUE_NAME}{tail}"


def disable() -> str:
    """删除 Run 项（以及旧版本留下的快捷方式）。"""
    import winreg

    removed_key = False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            try:
                winreg.DeleteValue(k, VALUE_NAME)
                removed_key = True
            except FileNotFoundError:
                pass
    except OSError:
        pass

    removed_link = _clear_legacy_shortcut()
    if removed_key or removed_link:
        return "已关闭开机自启动"
    return "开机自启动本来就是关闭的"
