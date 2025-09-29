# ProcPortManager

A command-line tool for managing processes, threads, and ports.

## Features

- Real-time process listing with CPU, memory, and thread count  
- Classification of processes into: System Idle, System, User, Services, Background, Other  
- Termination of process trees (terminate → wait → kill)  
- Find processes binding to a specified port and free the port  
- Display port ranges in grid format (FREE / OCCUPIED)  
- Real-time port monitoring  
- Thread monitor filtered by process name with interactive navigation  
- Save query outputs to JSON files in `Documents/ProcPortManager/` (filename + timestamp)  
- Colorized console output (optional with `colorama`)  
- Admin elevation attempt on Windows  

## Requirements

- Python 3.8+  
- `psutil`  
- `colorama` (optional, for colored output)  
- `wmi` (optional, Windows-only, for additional metadata)  

## Installation & Usage

```bash
git clone https://github.com/cheloei/ProcPortManager.git
cd ProcPortManager
pip install psutil colorama wmi
python main.py
```

## Modules & Structure

- `main.py` — entry point  
- `modules/config.py` — project constants and paths  
- `modules/utils.py` — utilities for printing, saving, admin elevation  
- `modules/process_manager.py` — process listing, classification, termination  
- `modules/port_manager.py` — port scanning, freeing, monitoring  
- `modules/monitor.py` — thread monitors and full process monitor  

## Usage Outline

1. **Show processes**: filter by thread type or show all  
2. **Search processes** by name or fragment  
3. **Kill process by PID** (with its children)  
4. **Kill processes by name**  
5. **Show Top processes** by CPU or memory  
6. **Free a port** by terminating owning process tree  
7. **Show ports in a range**  
8. **Real-time port monitor**  
9. **Monitor threads by process name**  
0. **Exit**

## Safety & Notes

- Terminating processes may cause data loss — use with caution  
- Freeing a port forcibly ends processes binding it  
- Process classification is heuristic-based, not guaranteed accurate  
- Windows service processes may resist termination  
- Color output requires compatible console and colorama  
