import tkinter as tk
from tkinter import ttk
import win32gui
import win32process
import win32con
import psutil
import subprocess
import time
import os

# --- 1. AUTOSTART CONFIGURATION ---
# Define applications to start if they are not already running.
# 'name': The process name (e.g., "notepad.exe"). Find this in Task Manager.
# 'path': The full, absolute path to the executable.
AUTOSTART_APPS = [
    {'name': 'reef.exe', 'path': os.path.expanduser('~/reef.exe')}
    #{'name': 'mspaint.exe', 'path': 'C:\\Windows\\System32\\mspaint.exe'},
    # Add your own apps here. Right-click a shortcut -> Properties to find the path.
    # {'name': 'Code.exe',    'path': 'C:\\Users\\YourUser\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe'},
]
WAIT_TIMEOUT = 15  # Seconds to wait for windows to appear after launching

# --- 2. PREDEFINED LAYOUT CONFIGURATION ---
# Define the desired layout for your windows.
# The script will wait for these windows to appear before arranging them.
DESIRED_LAYOUT = [
    #("notepad.exe", (0, 0, 800, 600)),
    #("Calculator",  (0, 600, 400, 500)),
    #("Window Manager",  (1505, 396, 416, 639)),
]

# --- 3. WINDOW MANIPULATION LOGIC ---

def find_window_by_exe(exe_name):
    """Finds a window handle (HWND) by its process's executable name."""
    # This helper function is used by both autostart and arrange logic
    target_hwnd = None
    def callback(hwnd, extra):
        nonlocal target_hwnd
        if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd):
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            if psutil.Process(pid).name().lower() == exe_name.lower():
                target_hwnd = hwnd
                return False # Stop searching
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return True
    win32gui.EnumWindows(callback, None)
    return target_hwnd

def find_window_by_title_substring(title_substring):
    """Finds a window handle (HWND) by a partial match of its title."""
    target_hwnd = None
    def callback(hwnd, extra):
        nonlocal target_hwnd
        if title_substring.lower() in win32gui.GetWindowText(hwnd).lower():
            target_hwnd = hwnd
            return False # Stop searching
        return True
    win32gui.EnumWindows(callback, None)
    return target_hwnd

def autostart_and_wait_for_windows():
    """Starts configured apps if not running, then waits for target windows to appear."""
    print("--- Starting Application Check ---")
    running_procs = {p.info['name'].lower() for p in psutil.process_iter(['name'])}
    
    apps_to_wait_for = [item[0] for item in DESIRED_LAYOUT]
    
    # 1. Start processes
    for app in AUTOSTART_APPS:
        app_name_lower = app['name'].lower()
        if app_name_lower not in running_procs:
            if os.path.exists(app['path']):
                print(f"Starting {app['name']}...")
                subprocess.Popen(app['path'])
            else:
                print(f"Warning: Path not found for {app['name']}: {app['path']}")
        else:
            print(f"{app['name']} is already running.")

    # 2. Wait for windows to appear
    print(f"\n--- Waiting for windows to open (timeout: {WAIT_TIMEOUT}s) ---")
    start_time = time.time()
    while time.time() - start_time < WAIT_TIMEOUT:
        found_all = True
        for identifier in apps_to_wait_for:
            hwnd = None
            if '.' in identifier: # It's an exe name
                hwnd = find_window_by_exe(identifier)
            else: # It's a title substring
                hwnd = find_window_by_title_substring(identifier)
            
            if not hwnd:
                found_all = False
                break # No need to check others, we are not ready yet
        
        if found_all:
            print("All target windows are open. Proceeding with arrangement.")
            return

        print("Waiting...", end='\r')
        time.sleep(0.5)

    print(f"\nTimeout reached. Proceeding with any windows that were found.")


def arrange_windows_on_startup():
    """Arranges windows based on the DESIRED_LAYOUT configuration."""
    print("\n--- Arranging Windows ---")
    for identifier, (x, y, width, height) in DESIRED_LAYOUT:
        hwnd = None
        if '.' in identifier:
            hwnd = find_window_by_exe(identifier)
        else:
            hwnd = find_window_by_title_substring(identifier)

        if hwnd:
            print(f"  > Arranging window for '{identifier}' (HWND: {hwnd})")
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            win32gui.MoveWindow(hwnd, x, y, width, height, True)
        else:
            print(f"  > Window for '{identifier}' not found, skipping arrangement.")
    print("--- Arrangement Complete ---\n")


# --- 4. GUI APPLICATION (No changes needed here) ---
class WindowManagerApp(tk.Tk):
    # (The entire WindowManagerApp class from the previous answer goes here, unchanged)
    # ... It's long, so I'm omitting it for brevity. Just copy-paste it.
    def __init__(self):
        super().__init__()
        self.title("Window Manager")
        self.geometry("400x600")
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill=tk.X)
        template_btn = ttk.Button(top_frame, text="Template Button", command=self.do_nothing)
        template_btn.pack(side=tk.LEFT, padx=(0, 10))
        refresh_btn = ttk.Button(top_frame, text="Refresh List", command=self.populate_window_list)
        refresh_btn.pack(side=tk.LEFT)
        self.canvas = tk.Canvas(self, borderwidth=0)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scrollable_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.populate_window_list()

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
        
    def do_nothing(self):
        print("Template button clicked. It does nothing for now!")

    def populate_window_list(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        windows = []
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                windows.append((hwnd, win32gui.GetWindowText(hwnd)))
        win32gui.EnumWindows(callback, None)
        for hwnd, title in sorted(windows, key=lambda item: item[1].lower()):
            btn = ttk.Button(self.scrollable_frame, text=title, command=lambda h=hwnd: self.show_window_info(h))
            btn.pack(fill=tk.X, padx=5, pady=2, expand=True)

    def show_window_info(self, hwnd):
        try:
            rect = win32gui.GetWindowRect(hwnd)
            x, y, right, bottom = rect
            width, height = right - x, bottom - y
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            exe_name = psutil.Process(pid).name()
            title = win32gui.GetWindowText(hwnd)
            print(f"---\n  Title: {title}\n  Executable: {exe_name}\n  Position: ({x}, {y})\n  Size: ({width}, {height})\n---")
        except Exception as e:
            print(f"Could not get info for HWND {hwnd}. It may have closed. Error: {e}")

# --- 5. SCRIPT EXECUTION ---
if __name__ == "__main__":
    # 1. Start required applications and wait for them to open
    autostart_and_wait_for_windows()

    # 2. Arrange the windows based on the layout config
    arrange_windows_on_startup()

    # 3. Launch the GUI manager
    app = WindowManagerApp()
    app.mainloop()