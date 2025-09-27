# menu.py
"""
User menu - ties together modules and provides a stable CLI.
"""

import os
import sys

from .config import THREAD_TYPES
from .utils import print_header, print_warning, print_success, print_error, clear_screen, is_admin, relaunch_as_admin, save_or_return_menu
from .process_manager import fetch_processes_real_time, terminate_process_tree
from .port_manager import free_port_interactive, show_ports_range, real_time_ports_monitor
from .monitor import monitor_threads_by_process_name, monitor_all_processes

def main_menu():
    # admin check on start (Windows)
    if os.name == 'nt' and not is_admin():
        print_warning("Admin privileges recommended for some operations. Attempting to relaunch with admin...")
        try:
            if relaunch_as_admin():
                print("Relaunch requested. Exiting current instance.")
                sys.exit(0)
        except Exception:
            pass
        print_warning("Continuing without admin privileges (some operations may fail).")

    while True:
        try:
            clear_screen()
            print_header("ProcPort Manager - Main Menu")
            print("1) Show processes")
            print("2) Search processes by name")
            print("3) Kill process by PID")
            print("4) Kill processes by name")
            print("5) Show Top processes (CPU / Memory)")
            print("6) Free a port")
            print("7) Show free/occupied ports in a range")
            print("8) Real-time ports monitor")
            print("9) Monitor threads by process name")
            print("0) Exit")
            choice = input("Enter your choice: ").strip()

            if choice == '1':
                procs = fetch_processes_real_time()
                print_header("Thread types")
                for i,t in enumerate(THREAD_TYPES,1):
                    print(f" {i}) {t}")
                print(" 0) All")
                sel = input("Select thread type (0-6): ").strip()
                filtered = []
                if sel == '0':
                    for cat in THREAD_TYPES:
                        print_header(cat)
                        cat_procs = [p for p in procs if p['category']==cat]
                        if not cat_procs:
                            print_error("  <none>")
                        for p in cat_procs:
                            print(f" PID:{p['pid']:6} CPU:{p['cpu']:5.1f}% MEM:{p['mem_human']:8} Name:{p['name'][:30]:30} User:{str(p['user'])[:20]:20} Threads:{len(p['threads'])}")
                        filtered.extend(cat_procs)
                        print()
                elif sel in [str(i) for i in range(1,len(THREAD_TYPES)+1)]:
                    typ = THREAD_TYPES[int(sel)-1]
                    print_header(f"Category: {typ}")
                    filtered = [p for p in procs if p['category']==typ]
                    if not filtered:
                        print_error("  <none>")
                    for p in filtered:
                        print(f" PID:{p['pid']:6} CPU:{p['cpu']:5.1f}% MEM:{p['mem_human']:8} Name:{p['name'][:30]:30} User:{str(p['user'])[:20]:20} Threads:{len(p['threads'])}")
                else:
                    print("Invalid selection.")
                save_or_return_menu(filtered, default_name="process_list")

            elif choice == '2':
                term = input("Enter process name or fragment: ").strip()
                if term:
                    procs = fetch_processes_real_time()
                    matched = [p for p in procs if term.lower() in (p['name'] or "").lower() or any(term.lower() in str(x).lower() for x in p.get('cmdline',[]))]
                    print_header(f"Search results for '{term}'")
                    if not matched:
                        print(" <none>")
                    for p in matched:
                        print(f" PID:{p['pid']:6} CPU:{p['cpu']:5.1f}% MEM:{p['mem_human']:8} Name:{p['name'][:30]:30} User:{str(p['user'])[:20]:20}")
                    save_or_return_menu(matched, default_name=f"search_{term}")

            elif choice == '3':
                s = input("Enter PID to kill: ").strip()
                try:
                    pid = int(s)
                except Exception:
                    print_error("Invalid PID.")
                    continue
                try:
                    p = __import__('psutil').Process(pid)
                    print(f"Found: PID={pid} Name={p.name()} Cmdline={' '.join(p.cmdline() or [])}")
                except Exception:
                    print_error("Process not found or inaccessible.")
                    continue
                confirm = input(f"Kill PID {pid} and all child processes? (y/n): ").strip().lower()
                if confirm != 'y':
                    print("Cancelled.")
                    continue
                res = terminate_process_tree(pid, timeout=5)
                if res.get("terminated"):
                    print_success(f"Gracefully terminated: {res.get('terminated')}")
                if res.get("killed"):
                    print_success(f"Forcibly killed: {res.get('killed')}")
                if res.get("failed"):
                    for pid_failed, err in res.get("failed"):
                        print_error(f"Failed PID {pid_failed}: {err}")

            elif choice == '4':
                frag = input("Enter process name fragment to kill: ").strip()
                if not frag:
                    print("Empty fragment.")
                    continue
                procs = fetch_processes_real_time()
                targets = [p for p in procs if frag.lower() in (p['name'] or '').lower()]
                if not targets:
                    print("No matching processes.")
                    continue
                print_header("Processes to be killed (with their children)")
                for p in targets:
                    print(f" PID:{p['pid']:6} Name:{p['name']}")
                confirm = input(f"Kill {len(targets)} processes and their children? (y/n): ").strip().lower()
                if confirm != 'y':
                    print("Cancelled.")
                    continue
                for p in targets:
                    pid = p['pid']
                    print_header(f"Terminating tree for PID {pid}")
                    res = terminate_process_tree(pid, timeout=5)
                    if res.get("terminated"):
                        print_success(f"Gracefully terminated: {res.get('terminated')}")
                    if res.get("killed"):
                        print_success(f"Forcibly killed: {res.get('killed')}")
                    if res.get("failed"):
                        for pid_failed, err in res.get("failed"):
                            print_error(f"Failed PID {pid_failed}: {err}")

            elif choice == '5':
                sort_choice = input("Sort by (1) CPU or (2) Memory? [1/2]: ").strip() or '1'
                n = input("How many results (default 5): ").strip()
                try:
                    n = int(n)
                    if n<=0: n=5
                except Exception:
                    n = 5
                procs = fetch_processes_real_time()
                if sort_choice == '1':
                    procs.sort(key=lambda x: x['cpu'], reverse=True)
                    out = procs[:n]
                    print_header(f"Top {n} by CPU")
                    for p in out:
                        print(f" PID:{p['pid']:6} CPU:{p['cpu']:5.1f}% MEM:{p['mem_human']:8} Name:{p['name']}")
                else:
                    procs.sort(key=lambda x: x['mem'], reverse=True)
                    out = procs[:n]
                    print_header(f"Top {n} by Memory")
                    for p in out:
                        print(f" PID:{p['pid']:6} MEM:{p['mem_human']:8} CPU:{p['cpu']:5.1f}% Name:{p['name']}")
                save_or_return_menu(out, default_name="top_processes")

            elif choice == '6':
                free_port_interactive()

            elif choice == '7':
                show_ports_range()

            elif choice == '8':
                try:
                    start = int(input("Start port: ").strip())
                    end = int(input("End port: ").strip())
                    interval = input("Interval seconds (default 5): ").strip()
                    try:
                        interval = float(interval) if interval else 5.0
                    except Exception:
                        interval = 5.0
                    real_time_ports_monitor(start, end, interval)
                except KeyboardInterrupt:
                    print("\nReturning to main menu...")
                except Exception as e:
                    print_error(f"Invalid input or error: {e}")

            elif choice == '9':
                name = input("Process name substring to monitor: ").strip()
                if name:
                    try:
                        interval = input("Interval seconds (default 2): ").strip()
                        try:
                            interval = float(interval) if interval else 2.0
                        except Exception:
                            interval = 2.0
                        monitor_threads_by_process_name(name, interval=interval)
                    except KeyboardInterrupt:
                        print("\nReturning to main menu...")

            elif choice == '10':
                try:
                    interval = input("Interval seconds (default 5): ").strip()
                    try:
                        interval = float(interval) if interval else 5.0
                    except Exception:
                        interval = 5.0
                    monitor_all_processes(interval=interval)
                except KeyboardInterrupt:
                    print("\nReturning to main menu...")
            elif choice == '0':
                print("Goodbye.")
                break
            else:
                print("Invalid choice. Try again.")
        except KeyboardInterrupt:
            print("\nReturning to main menu...")
