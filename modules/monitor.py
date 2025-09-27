# monitor.py
"""
Improved thread monitor display (interactive).
- monitor_threads_by_process_name(name, interval)
- monitor_all_processes(interval)
"""

import time
import psutil
from typing import List, Dict

from .utils import clear_screen, print_header, print_error, print_success

def _format_mem(n: int) -> str:
    try:
        return f"{n/1024/1024:.2f}MB"
    except Exception:
        return str(n)

def _fetch_matching_processes(filter_name: str) -> List[Dict]:
    """
    Fetch processes matched by filter_name (case-insensitive).
    Returns list with fields: pid, name, thread_count, cpu, mem
    """
    procs = []
    # warm CPU sampling
    for p in psutil.process_iter(attrs=['pid']):
        try:
            p.cpu_percent(interval=None)
        except Exception:
            pass
    time.sleep(0.05)
    for p in psutil.process_iter(attrs=['pid','name','memory_info','cmdline']):
        try:
            name = p.info.get('name') or "<unknown>"
            if filter_name and filter_name.lower() not in name.lower():
                continue
            pid = int(p.info.get('pid') or 0)
            try:
                cpu = p.cpu_percent(interval=None)
            except Exception:
                cpu = 0.0
            mem = (p.info.get('memory_info').rss if p.info.get('memory_info') else 0)
            try:
                threads = p.threads()
                thread_count = len(threads)
            except Exception:
                thread_count = 0
            procs.append({
                "pid": pid,
                "name": name,
                "thread_count": thread_count,
                "cpu": cpu,
                "mem": mem,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return procs

def _print_table(rows: List[Dict], page_size: int, page: int = 0):
    start = page * page_size
    end = start + page_size
    subset = rows[start:end]
    print(f"{'Idx':>3}  {'PID':>6}  {'Threads':>7}  {'CPU%':>6}  {'MEM':>8}  {'Name'}")
    print("-"*80)
    for i, r in enumerate(subset, start=1+start):
        name = (r['name'][:35] + '...') if len(r['name']) > 38 else r['name']
        print(f"{i:3}  {r['pid']:6}  {r['thread_count']:7}  {r['cpu']:6.1f}  {_format_mem(r['mem']):>8}  {name}")

def _show_threads_of_pid(pid: int):
    try:
        p = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print_error(f"Process {pid} no longer exists.")
        return
    except Exception as e:
        print_error(f"Cannot access PID {pid}: {e}")
        return

    try:
        tlist = p.threads()
    except Exception as e:
        print_error(f"Cannot retrieve threads for PID {pid}: {e}")
        return

    print_header(f"Threads for PID {pid} - {p.name()}")
    if not tlist:
        print(" <no threads>")
        return
    print(f"{'TID':>8}  {'UserTime':>10}  {'SystemTime':>11}")
    print("-"*40)
    for t in tlist:
        tid = getattr(t, 'id', None)
        u = getattr(t, 'user_time', 0.0)
        s = getattr(t, 'system_time', 0.0)
        print(f"{tid:8}  {u:10.4f}  {s:11.4f}")
    print("-"*40)

def monitor_threads_by_process_name(filter_name: str = "", interval: float = 2.0, page_size: int = 20):
    """
    Interactive monitor:
    Controls:
      Enter -> refresh
      <pid> -> show detailed threads for PID (or index)
      n -> next page, p -> prev page
      r -> change filter
      s -> change page size
      q -> quit (return to menu)
    Ctrl+C also returns to menu.
    """
    current_filter = filter_name or ""
    current_page = 0

    try:
        while True:
            clear_screen()
            header_text = f"Thread Monitor - filter='{current_filter or '*all*'}'  (page {current_page+1})"
            print_header(header_text)
            procs = _fetch_matching_processes(current_filter)
            if not procs:
                print(" <no matching processes>")
            else:
                procs.sort(key=lambda x: (x['thread_count'], x['cpu']), reverse=True)
                total_pages = max(1, (len(procs) + page_size - 1) // page_size)
                if current_page >= total_pages:
                    current_page = 0
                _print_table(procs, page_size, page=current_page)
                print("\nControls: [Enter]=refresh   [pid]=show threads   n=next page   p=prev page   r=change filter   s=page size   q=quit")
                cmd = input("Command: ").strip()
                if cmd == "":
                    continue
                if cmd.lower() == 'q':
                    break
                if cmd.lower() == 'n':
                    current_page = (current_page + 1) % total_pages
                    continue
                if cmd.lower() == 'p':
                    current_page = (current_page - 1) % total_pages
                    continue
                if cmd.lower() == 'r':
                    current_filter = input("Enter new filter substring (empty = all): ").strip()
                    current_page = 0
                    continue
                if cmd.lower() == 's':
                    try:
                        newsize = int(input("Enter new page size (rows): ").strip())
                        if newsize > 0:
                            page_size = newsize
                            current_page = 0
                        else:
                            print_error("Invalid page size.")
                    except Exception:
                        print_error("Invalid number.")
                    continue
                # numeric -> PID or index
                if cmd.isdigit():
                    num = int(cmd)
                    # check PID match
                    matched = [r for r in procs if r['pid'] == num]
                    if matched:
                        clear_screen()
                        _show_threads_of_pid(num)
                        input("\nPress Enter to return to monitor...")
                        continue
                    total = len(procs)
                    if 1 <= num <= total:
                        selected = procs[num-1]
                        clear_screen()
                        _show_threads_of_pid(selected['pid'])
                        input("\nPress Enter to return to monitor...")
                        continue
                    print_error("No matching PID or index in list.")
                    time.sleep(1.0)
                    continue
                print_error("Unknown command.")
                time.sleep(0.6)
            # if no procs
            print("\nControls: [Enter]=refresh   r=change filter   q=quit")
            cmd = input("Command: ").strip()
            if cmd == "":
                continue
            if cmd.lower() == 'q':
                break
            if cmd.lower() == 'r':
                current_filter = input("Enter new filter substring (empty = all): ").strip()
                current_page = 0
                continue
    except KeyboardInterrupt:
        print("\nReturning to main menu...")
        return

def monitor_all_processes(interval: float = 5.0):
    """Simple full-process monitor (basic info)."""
    try:
        while True:
            clear_screen()
            print_header("All Processes")
            for proc in psutil.process_iter(['pid','name','cpu_percent','memory_percent']):
                try:
                    print(f"PID:{proc.info['pid']:6} Name:{proc.info['name'][:25]:25} CPU:{proc.info['cpu_percent']:5.1f}% Mem:{proc.info['memory_percent']:5.1f}%")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nReturning to main menu...")
        return
