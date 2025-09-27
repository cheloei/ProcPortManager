# config.py
"""
Configuration for ProcPort Manager.
"""

from pathlib import Path

PROJECT_NAME = "ProcPortManager"
DOCUMENTS_DIR = Path.home() / "Documents" / PROJECT_NAME
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

THREAD_TYPES = [
    "System",
    "User",
    "Services",
    "Background",
    "Other",
]

PORT_SCAN_ROW_WIDTH = 8
DEFAULT_PORT_MONITOR_INTERVAL = 5.0
DEFAULT_THREAD_MONITOR_INTERVAL = 3.0
