"""
KanoonVault Windows Application Launcher
Handles:
- Setting up user data directories (%APPDATA%\\KanoonVault\\)
- Starting FastAPI backend
- Opening browser automatically
- Graceful shutdown
"""

import os
import sys
import json
import webbrowser
import subprocess
import time
import shutil
import atexit
from pathlib import Path
from threading import Thread
import signal


def setup_user_data_directory():
    """
    Create and return the user data directory path.
    On Windows, this is %LOCALAPPDATA%\\KanoonVault\\
    
    Returns:
        Path: User data directory
    """
    if sys.platform == "win32":
        localappdata = os.getenv("LOCALAPPDATA")
        if not localappdata:
            localappdata = str(Path.home() / "AppData" / "Local")
        user_data_dir = Path(localappdata) / "KanoonVault"
    else:
        # For non-Windows (fallback)
        user_data_dir = Path.home() / ".KanoonVault"
    
    user_data_dir.mkdir(parents=True, exist_ok=True)
    return user_data_dir


def setup_subdirectories(user_data_dir: Path):
    """Create required subdirectories in user data directory."""
    subdirs = ["uploads", "chroma_db", "logs"]
    for subdir in subdirs:
        (user_data_dir / subdir).mkdir(exist_ok=True)


def get_env_path(user_data_dir: Path):
    """Get path to .env file in user data directory."""
    return user_data_dir / ".env"


def copy_env_template_if_needed(user_data_dir: Path):
    """
    Copy .env.example to user data .env if it doesn't exist.
    This allows users to configure API keys without editing the bundled app.
    """
    env_path = get_env_path(user_data_dir)
    if env_path.exists():
        return  # Don't overwrite existing .env
    
    # Try to find .env.example in the bundled app directory
    app_dir = Path(sys.argv[0]).parent if hasattr(sys, 'frozen') else Path(__file__).parent
    env_example = app_dir / ".env.example"
    
    if env_example.exists():
        shutil.copy(str(env_example), str(env_path))
        print(f"[*] Created .env template at {env_path}")
    else:
        # Create a minimal .env file
        env_content = """# KanoonVault Configuration
# Copy your OpenRouter API key here

# Chat
OPENROUTER_API_KEY=
OPENROUTER_MODEL=z-ai/glm-4.5-air:free

# Vision OCR
OCR_VISION_API_KEY=
OCR_VISION_MODEL=google/gemma-4-31b-it:free

# Timeline extraction
TIMELINE_API_KEY=
TIMELINE_MODEL=google/gemma-4-31b-it:free

MAX_CONTEXT_CHARS=6000
"""
        env_path.write_text(env_content)
        print(f"[*] Created minimal .env at {env_path}")


def setup_environment_variables(user_data_dir: Path):
    """
    Set environment variables to point to user data directory.
    This redirects the application to use user paths instead of bundled paths.
    """
    env_path = get_env_path(user_data_dir)
    
    # Set environment variables
    os.environ["KANOONVAULT_USER_DATA_DIR"] = str(user_data_dir)
    os.environ["KANOONVAULT_UPLOAD_DIR"] = str(user_data_dir / "uploads")
    os.environ["KANOONVAULT_CHROMA_DB"] = str(user_data_dir / "chroma_db")
    os.environ["KANOONVAULT_DB_PATH"] = str(user_data_dir / "kanoonvault.db")
    
    # Load .env file if it exists
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value


def get_app_module():
    """
    Get the FastAPI app module.
    In development: import main directly
    In packaged app: the main module is available via PyInstaller
    """
    try:
        import main
        return main
    except ImportError as e:
        print(f"[ERROR] Failed to import main module: {e}")
        sys.exit(1)


def override_database_paths():
    """
    Override hardcoded database paths in the application modules.
    This is called after environment variables are set and before the app starts.
    """
    user_data_dir = Path(os.environ.get("KANOONVAULT_USER_DATA_DIR"))
    
    # Override database.py paths
    import database as db
    db.DB_PATH = user_data_dir / "kanoonvault.db"
    
    # Override main.py paths
    import main
    main.UPLOAD_DIR = user_data_dir / "uploads"
    
    # Override vector_memory_service paths
    from services import vector_memory_service
    vector_memory_service.CHROMA_PATH = str(user_data_dir / "chroma_db")
    # Reinitialize the ChromaDB client with new path
    import chromadb
    vector_memory_service.chroma_client = chromadb.PersistentClient(
        path=str(user_data_dir / "chroma_db")
    )


def open_browser(port=8000, max_retries=30, retry_delay=1):
    """
    Wait for the server to be ready, then open browser.
    
    Args:
        port: The port the FastAPI server is running on
        max_retries: Maximum number of retries to check if server is ready
        retry_delay: Delay between retries in seconds
    """
    import socket
    
    url = f"http://127.0.0.1:{port}"
    
    for attempt in range(max_retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            
            if result == 0:
                print(f"[*] Server is ready. Opening {url} in browser...")
                webbrowser.open(url)
                return
        except Exception as e:
            pass
        
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    print(f"[WARN] Server did not become ready. Tried to open {url} anyway.")
    webbrowser.open(url)


def start_fastapi_server(port=8000, host="127.0.0.1"):
    """
    Start the FastAPI server using Uvicorn.
    
    Args:
        port: Port to bind the server to
        host: Host to bind the server to (127.0.0.1 for localhost only)
    """
    try:
        import uvicorn
        import main
        
        print(f"[*] Starting KanoonVault on {host}:{port}")
        
        # Run Uvicorn server
        # reload=False to disable development reload
        # log_level="info" for standard logging
        uvicorn.run(
            main.app,
            host=host,
            port=port,
            log_level="info",
            access_log=False,
        )
    except Exception as e:
        print(f"[ERROR] Failed to start FastAPI server: {e}")
        sys.exit(1)


def run_server_in_thread(port=8000, host="127.0.0.1"):
    """
    Run the FastAPI server in a background thread.
    
    Returns:
        threading.Thread: The server thread
    """
    server_thread = Thread(
        target=start_fastapi_server,
        args=(port, host),
        daemon=True,
    )
    server_thread.start()
    return server_thread


def cleanup():
    """Cleanup function called on application exit."""
    print("\n[*] Shutting down KanoonVault...")


def main():
    """Main launcher entry point."""
    print("\n")
    print("=" * 60)
    print("  KanoonVault - Legal Memory OS")
    print("=" * 60)
    print()
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))
    
    # Setup user data directory
    print("[*] Setting up user data directory...")
    user_data_dir = setup_user_data_directory()
    print(f"[*] User data directory: {user_data_dir}")
    
    # Create subdirectories
    setup_subdirectories(user_data_dir)
    
    # Copy .env template if needed
    copy_env_template_if_needed(user_data_dir)
    
    # Setup environment variables (including loading .env)
    setup_environment_variables(user_data_dir)
    
    # Import app after environment is set up
    print("[*] Loading application...")
    try:
        import main
        import database as db
        from services import vector_memory_service
    except ImportError as e:
        print(f"[ERROR] Failed to import application: {e}")
        sys.exit(1)
    
    # Override hardcoded paths
    print("[*] Configuring data paths...")
    override_database_paths()
    
    # Register cleanup on exit
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda sig, frame: cleanup())
    
    # Start FastAPI server in background thread
    print("[*] Starting FastAPI server...")
    server_thread = run_server_in_thread(port)
    
    browser_thread = Thread(
        target=open_browser,
        args=(port,),
        daemon=True,
    )
    browser_thread.start()
    
    # Keep the launcher alive so the packaged EXE stays running.
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
