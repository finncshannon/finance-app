"""
Company Intelligence Screener -- Application Entry Point.

Launch:
    python app.py
    OR
    double-click launch_screener.bat
"""

import sys
import os
from pathlib import Path

# Ensure the Screening_Tool directory is in the Python path
app_dir = Path(__file__).parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# Work from the app directory (needed for relative paths to config/, data/)
os.chdir(str(app_dir))

import tkinter as tk
from gui.main_window import MainWindow


def main():
    root = tk.Tk()

    # Set DPI awareness for crisp text on high-DPI displays (Windows 10+)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = MainWindow(root)

    # Handle clean exit
    root.protocol('WM_DELETE_WINDOW', root.destroy)
    root.mainloop()


if __name__ == '__main__':
    main()
