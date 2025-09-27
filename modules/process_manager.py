# process_manager.py
"""
Process management utilities:
- real-time fetching
- categorize
- terminate process tree (safe)
- convenience helpers used by menu
"""

import time
import psutil
from typing import List, Dict

from .config import THREAD_TYPES
from .utils import print_header, print_success, print_error, print_warning, save_or_return_menu

def human_mem_mb(n: int) -> str:
    """Return human readable memory MB string."""
    try:
        return f"{n/1024/1024:.1f} MB"
    except Exception:
        return str(n)

def categorize_process(pid: int, name: str, username: str):
    """Categorize process into configured THREAD_TYPES (heuristics)."""
    try:
        if pid == 0:
            return "System Idle"
        if pid <= 4:
            return "System"
        if username is None:
            return "Background"
        uname = str(username).upper()
        lname = (name or "").lower()
        if 'service' in lname or uname == 'SYSTEM' or uname.startswith('NT AUTHORITY'):
            return "Services"
        return "User"
    except Exception:
        return "Other"

def fetch_processes_real_time() -> List[Dict]:
    """
    Snapshot current processes. No caching.
    Each entry: pid, name, user, cpu, mem, mem_human, category, exe, cmdline, threads
    """
    procs = []
    # prepare cpu sampling
    for p in psutil.process_iter(attrs=['pid']):
        try:
            p.cpu_percent(interval=None)
        except Exception:
            pass
    time.sleep(0.1)
    for p in psutil.process_iter(attrs=['pid','name','username','memory_info','exe','cmdline']):
        try:
            info = p.info
            pid = int(info.get('pid') or 0)
            name = info.get('name') or "<unknown>"
            user = info.get('username')
            try:
                cpu = p.cpu_percent(interval=None)
            except Exception:
                cpu = 0.0
            mem = (info.get('memory_info').rss if info.get('memory_info') else 0)
            exe = info.get('exe')
            cmdline = info.get('cmdline') or []
            category = categorize_process(pid, name, user)
            try:
                threads = [t.id for t in p.threads()]
            except Exception:
                threads = []
            procs.append({
                "pid": pid,
                "name": name,
                "user": user,
                "cpu": cpu,
                "mem": mem,
                "mem_human": human_mem_mb(mem),
                "category": category,
                "exe": exe,
                "cmdline": cmdline,
                "threads": threads
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return procs

def terminate_process_tree(pid: int, timeout: float = 5.0) -> Dict:
    """
    Terminate a process and its child processes safely.

    Strategy:
      1. Collect children recursively (children first).
      2. Call terminate() on all (graceful).
      3. wait for `timeout` seconds using psutil.wait_procs.
      4. Call kill() on remaining alive processes.
    Returns:
      dict { 'terminated': [pids], 'killed': [pids], 'failed': [(pid, msg), ...] }
    """
    result = {"terminated": [], "killed": [], "failed": []}
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return result
    except Exception as e:
        result["failed"].append((pid, f"cannot access process: {e}"))
        return result

    try:
        children = parent.children(recursive=True)
    except Exception:
        children = []

    # stable list children first
    all_procs = []
    for c in children:
        try:
            all_procs.append(psutil.Process(c.pid))
        except Exception:
            continue
    all_procs.append(parent)

    # attempt graceful terminate
    for p in all_procs:
        try:
            p.terminate()
        except Exception as e:
            result["failed"].append((getattr(p,'pid',None), f"terminate error: {e}"))

    # wait for termination
    try:
        gone, alive = psutil.wait_procs(all_procs, timeout=timeout)
    except Exception:
        gone = []
        alive = [p for p in all_procs if p.is_running()]

    for p in gone:
        try:
            result["terminated"].append(p.pid)
        except Exception:
            pass

    # force kill remaining alive
    if alive:
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                result["terminated"].append(getattr(p,'pid',None))
            except Exception as e:
                result["failed"].append((getattr(p,'pid',None), f"kill error: {e}"))

        try:
            gone2, alive2 = psutil.wait_procs(alive, timeout=3)
            for p in gone2:
                if p.pid not in result["terminated"]:
                    result["killed"].append(p.pid)
            for p in alive2:
                result["failed"].append((getattr(p,'pid',None), "still alive after kill"))
        except Exception:
            for p in alive:
                try:
                    if not p.is_running():
                        if p.pid not in result["terminated"]:
                            result["killed"].append(p.pid)
                    else:
                        result["failed"].append((getattr(p,'pid',None), "still alive after kill"))
                except Exception:
                    result["failed"].append((getattr(p,'pid',None), "unknown state"))

    # clean lists
    result["terminated"] = list(dict.fromkeys([x for x in result["terminated"] if x]))
    result["killed"] = list(dict.fromkeys([x for x in result["killed"] if x and x not in result["terminated"]]))
    result["failed"] = [(pid,msg) for pid,msg in result["failed"] if pid]

    return result
