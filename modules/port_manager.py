# port_manager.py
"""
Port management utilities:
- find processes using a port
- free a port (terminating process trees and dependencies)
- show ports range as grid (colored)
- real-time monitor (no save prompt)
"""

import socket
import time
import psutil

from .config import PORT_SCAN_ROW_WIDTH, DEFAULT_PORT_MONITOR_INTERVAL
from .utils import print_header, print_success, print_warning, print_error, color_text, save_or_return_menu, clear_screen
from .process_manager import terminate_process_tree

def find_processes_using_port(port: int):
    """Return list of psutil.Process objects that use given port (listening or connected)."""
    procs = []
    try:
        for conn in psutil.net_connections(kind='inet'):
            try:
                if conn.laddr and getattr(conn.laddr, 'port', None) == port and conn.pid:
                    procs.append(psutil.Process(conn.pid))
            except Exception:
                continue
    except Exception:
        pass
    # dedupe by pid
    unique = {}
    for p in procs:
        unique[p.pid] = p
    return list(unique.values())

def free_port_interactive():
    """
    Interactive flow to free a port:
     - show processes using port
     - confirm termination
     - terminate process trees (children first)
     - re-check port and offer save
    """
    try:
        s = input("Enter port to free: ").strip()
        if not s:
            print("No port provided.")
            return
        port = int(s)
    except ValueError:
        print_error("Invalid port.")
        return

    procs = find_processes_using_port(port)
    if not procs:
        print_success(f"Port {port} is FREE")
        return

    print_header(f"Processes using port {port}")
    candidates = []
    for p in procs:
        try:
            exe = p.exe() or None
        except Exception:
            exe = None
        try:
            user = p.username()
        except Exception:
            user = None
        display = f" PID:{p.pid:6} Name:{p.name()[:30]:30} User:{str(user)[:20]:20} Exe:{exe or '-'}"
        print(display)
        candidates.append({"pid": p.pid, "name": p.name(), "user": user, "exe": exe, "cmdline": p.cmdline() if hasattr(p,'cmdline') else []})

    confirm = input("Terminate these processes and their children to free the port? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return

    # terminate each candidate's process tree
    total_summary = {"terminated": [], "killed": [], "failed": []}
    for c in candidates:
        pid = c["pid"]
        print_header(f"Terminating tree for PID {pid}")
        res = terminate_process_tree(pid, timeout=5)
        total_summary["terminated"].extend(res.get("terminated", []))
        total_summary["killed"].extend(res.get("killed", []))
        total_summary["failed"].extend(res.get("failed", []))
        if res.get("terminated"):
            print_success(f"Gracefully terminated: {res.get('terminated')}")
        if res.get("killed"):
            print_success(f"Forcibly killed: {res.get('killed')}")
        if res.get("failed"):
            for pid_failed, err in res.get("failed"):
                print_error(f"Failed PID {pid_failed}: {err}")

    time.sleep(0.3)
    still = find_processes_using_port(port)
    if still:
        print_warning(f"Port {port} still appears in use. Manual inspection recommended.")
    else:
        print_success(f"Port {port} is now FREE")

    payload = {"candidates": candidates, "summary": total_summary}
    save_or_return_menu(payload, default_name=f"port_{port}_processes")

def show_ports_range():
    """Show ports in a grid, colored, and offer save."""
    try:
        start = int(input("Start port: ").strip())
        end = int(input("End port: ").strip())
    except ValueError:
        print_error("Invalid input.")
        return
    if start < 1 or end > 65535 or start > end:
        print_error("Invalid range.")
        return

    results = []
    print_header(f"Ports {start}..{end}")
    col = 0
    for port in range(start, end+1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.02)
            occupied = s.connect_ex(("127.0.0.1", port)) == 0
            status = "OCCUPIED" if occupied else "FREE"
        display = f"{port:5}:{status}"
        print(color_text(display, status), end="   ")
        results.append({"port": port, "status": status})
        col += 1
        if col % PORT_SCAN_ROW_WIDTH == 0:
            print()
    print("\n")
    save_or_return_menu(results, default_name=f"ports_{start}_{end}")

def real_time_ports_monitor(start: int, end: int, interval: float = DEFAULT_PORT_MONITOR_INTERVAL):
    """
    Real-time monitoring loop for ports. No save prompt.
    Ctrl+C returns to menu.
    """
    try:
        while True:
            clear_screen()
            print_header(f"Real-time ports {start}-{end} (interval {interval}s) - Ctrl+C to stop")
            col = 0
            for port in range(start, end+1):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.02)
                    occupied = s.connect_ex(("127.0.0.1", port)) == 0
                    status = "OCCUPIED" if occupied else "FREE"
                display = f"{port:5}:{status}"
                print(color_text(display, status), end="   ")
                col += 1
                if col % PORT_SCAN_ROW_WIDTH == 0:
                    print()
            print("\n(Press Ctrl+C to stop monitoring)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopping port monitor and returning to menu.")
