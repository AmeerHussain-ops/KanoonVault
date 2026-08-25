"""
Native Folder Dialog Helper for Windows/Cross-platform

Provides folder selection dialog using tkinter or ctypes.
"""

import os
import sys
from pathlib import Path


def select_folder(title: str = "Select Folder", initial_dir: str = None) -> str | None:
    """
    Open a native folder selection dialog.
    
    Args:
        title: Dialog title
        initial_dir: Initial directory to show
        
    Returns:
        Selected folder path or None if cancelled
    """
    
    # Try tkinter first (cross-platform, usually available with Python)
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # Create a hidden root window
        root = tk.Tk()
        root.withdraw()  # Hide the window
        root.attributes('-topmost', True)  # Bring to front
        
        if initial_dir and Path(initial_dir).exists():
            folder = filedialog.askdirectory(
                title=title,
                initialdir=initial_dir
            )
        else:
            folder = filedialog.askdirectory(title=title)
        
        root.destroy()
        
        if folder and folder.strip():
            return folder
        else:
            return None
            
    except Exception as e:
        print(f"[Dialog] Tkinter folder dialog failed: {e}")
    
    # Fallback for Windows using ctypes (if tkinter is not available)
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import windll
            
            # Windows folder selection dialog using ctypes
            # This is a simplified version - for production, use ctypes IFileDialog
            print("[Dialog] Tkinter not available, falling back to shell dialog")
            
            # Use Windows shell browse dialog via COM if available
            try:
                import win32api
                from win32 import win32gui
                
                pidl, display_name, image_list = win32api.SHBrowseForFolder(
                    win32gui.GetDesktopWindow(),
                    None,
                    title,
                    0x0040  # BIF_RETURNONLYFSDIRS
                )
                
                if pidl:
                    folder = win32api.SHGetPathFromIDList(pidl)
                    return folder
            except ImportError:
                pass
        except Exception as e:
            print(f"[Dialog] Windows folder dialog failed: {e}")
    
    # Final fallback - return None (caller should use default)
    print("[Dialog] No native folder dialog available")
    return None


def is_valid_folder(path: str) -> bool:
    """
    Check if a path is a valid folder for storage.
    
    Args:
        path: Path to check
        
    Returns:
        True if valid
    """
    if not path or not isinstance(path, str):
        return False
    
    try:
        p = Path(path)
        
        # Check if it's an absolute path
        if not p.is_absolute():
            return False
        
        # Check if it exists or can be created
        if not p.exists():
            # Try to create it
            p.mkdir(parents=True, exist_ok=True)
        
        # Check if it's writable
        if not os.access(str(p), os.W_OK):
            return False
        
        return True
    except Exception:
        return False
