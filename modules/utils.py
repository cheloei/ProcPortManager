# utils.py
"""
Common utilities: color init, printing helpers, saving helper, admin helpers.
All user-facing text in this file remains English.
"""

import os
import json
import ctypes
from datetime import datetime
from pathlib import Path

from .config import DOCUMENTS_DIR

# try colorama
try:
    from colorama import Fore, Style, init as colorama_init
    COLORAMA_AVAILABLE = True
    try:
        colorama_init(autoreset=True)
    except Exception:
        pass
except Exception:
    COLORAMA_AVAILABLE = False
    class _Dummy:
        def __getattr__(self, name):
            return ""
    Fore = Style = _Dummy()

# Try enable VT mode on Windows to make ANSI escapes work reliably
def _enable_windows_vt_mode():
    if os.name != 'nt':
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        hStdOut = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(hStdOut, ctypes.byref(mode)) == 0:
            return False
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
        if kernel32.SetConsoleMode(hStdOut, new_mode) == 0:
            return False
        return True
    except Exception:
        return False

try:
    _enable_windows_vt_mode()
except Exception:
    pass

def timestamp_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title: str):
    if COLORAMA_AVAILABLE:
        print(Fore.CYAN + "====== " + title + " ======" + Style.RESET_ALL)
    else:
        print("====== " + title + " ======")

def print_success(msg: str):
    if COLORAMA_AVAILABLE:
        print(Fore.GREEN + msg + Style.RESET_ALL)
    else:
        print(msg)

def print_warning(msg: str):
    if COLORAMA_AVAILABLE:
        print(Fore.YELLOW + msg + Style.RESET_ALL)
    else:
        print(msg)

def print_error(msg: str):
    if COLORAMA_AVAILABLE:
        print(Fore.RED + msg + Style.RESET_ALL)
    else:
        print(msg)

def color_text(text: str, status: str):
    """
    Colorize a short text by status.
    status: 'OCCUPIED' -> red, 'FREE' -> green, others -> default.
    """
    if not COLORAMA_AVAILABLE:
        return text
    s = (status or "").upper()
    if s == "OCCUPIED":
        return Fore.RED + text + Style.RESET_ALL
    if s == "FREE":
        return Fore.GREEN + text + Style.RESET_ALL
    if s in ("WARN", "WARNING"):
        return Fore.YELLOW + text + Style.RESET_ALL
    return text

def is_admin():
    """
    Return True if running as admin on Windows.
    Non-windows returns True (no elevation concept here).
    """
    if os.name != 'nt':
        return True
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def relaunch_as_admin():
    """
    Try to relaunch the running script with UAC on Windows.
    Returns True if launch requested (current process should exit).
    """
    if os.name != 'nt':
        return False
    try:
        script = os.path.abspath(os.path.realpath(__file__))
        # relaunch main module instead of utils file: use sys.executable and module entry from main.py
        # We'll try relaunching the current python interpreter with the script that started the process
        import sys
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{p}"' for p in sys.argv[1:]])
        python_exe = sys.executable
        ctypes.windll.shell32.ShellExecuteW(None, "runas", python_exe, f'"{script}" {params}', None, 1)
        return True
    except Exception:
        return False

def save_or_return_menu(data, default_name="results"):
    """
    Ask user to save results to JSON in Documents/PROJECT folder, or return.
    Returns after saving or returning. Catches KeyboardInterrupt and returns.
    """
    try:
        while True:
            print("\nOptions:")
            print(" 1) Save results to file")
            print(" 2) Return to main menu")
            choice = input("Choose an option (1-2): ").strip()
            if choice == "1":
                fname = input(f"Enter filename without extension [{default_name}]: ").strip() or default_name
                filename = f"{fname}_{timestamp_str()}.json"
                path = Path(DOCUMENTS_DIR) / filename
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
                    print_success(f"Saved results to: {path}")
                    input("Enter to continue ...")
                except Exception as e:
                    print_error(f"Failed to save: {e}")
                    input("Enter to continue ...")
                return
            elif choice == "2":
                return
            else:
                print("Invalid selection. Enter 1 or 2.")
    except KeyboardInterrupt:
        print("\nReturning to main menu...")
        return
