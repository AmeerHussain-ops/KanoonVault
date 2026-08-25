"""
KanoonVault Storage Management

Handles:
- Storage location configuration (default or custom)
- Data directory initialization
- Data migration when storage location changes
- Settings persistence
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime


DEFAULT_STORAGE_DIR_WIN = Path.home() / "AppData" / "Local" / "KanoonVault"
DEFAULT_STORAGE_DIR_UNIX = Path.home() / ".KanoonVault"


def get_default_storage_dir() -> Path:
    """Get the default storage directory based on OS."""
    import sys
    if sys.platform == "win32":
        return DEFAULT_STORAGE_DIR_WIN
    else:
        return DEFAULT_STORAGE_DIR_UNIX


def get_config_file() -> Path:
    """Get the path to the storage configuration file."""
    config_base = Path.home() / "AppData" / "Roaming" if sys.platform == "win32" else Path.home()
    config_dir = config_base / ".kanoonvault"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "storage-config.json"


def load_storage_config() -> dict:
    """
    Load storage configuration from file.
    
    Returns:
        dict with keys: storage_dir (Path), first_run_complete (bool)
    """
    config_file = get_config_file()
    
    if not config_file.exists():
        # First run - use default
        return {
            "storage_dir": get_default_storage_dir(),
            "first_run_complete": False,
            "created_at": datetime.now().isoformat()
        }
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Ensure storage_dir is a Path object
        if "storage_dir" in data and isinstance(data["storage_dir"], str):
            data["storage_dir"] = Path(data["storage_dir"])
        else:
            data["storage_dir"] = get_default_storage_dir()
        
        return data
    except Exception as e:
        print(f"[Storage] Error loading config: {e}")
        return {
            "storage_dir": get_default_storage_dir(),
            "first_run_complete": False
        }


def save_storage_config(storage_dir: Path, first_run_complete: bool = False) -> bool:
    """
    Save storage configuration to file.
    
    Args:
        storage_dir: Path to storage directory
        first_run_complete: Whether first-run setup is complete
        
    Returns:
        True if successful
    """
    try:
        config_file = get_config_file()
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "storage_dir": str(storage_dir),
            "first_run_complete": first_run_complete,
            "updated_at": datetime.now().isoformat()
        }
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"[Storage] Error saving config: {e}")
        return False


def get_current_storage_dir() -> Path:
    """Get the currently configured storage directory."""
    config = load_storage_config()
    storage_dir = config.get("storage_dir")
    if isinstance(storage_dir, str):
        storage_dir = Path(storage_dir)
    return storage_dir or get_default_storage_dir()


def is_first_run_complete() -> bool:
    """Check if first-run setup has been completed."""
    config = load_storage_config()
    return config.get("first_run_complete", False)


def initialize_storage_directory(storage_dir: Path) -> bool:
    """
    Initialize storage directory with necessary subdirectories.
    
    Args:
        storage_dir: Path to storage directory
        
    Returns:
        True if successful
    """
    try:
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        subdirs = ["uploads", "chroma_db", "logs"]
        for subdir in subdirs:
            (storage_dir / subdir).mkdir(exist_ok=True)
        
        return True
    except Exception as e:
        print(f"[Storage] Error initializing directory: {e}")
        return False


def migrate_data(old_dir: Path, new_dir: Path) -> dict:
    """
    Migrate data from old storage directory to new one.
    
    Creates a backup of the old directory before migration.
    
    Args:
        old_dir: Current storage directory
        new_dir: New storage directory
        
    Returns:
        dict with migration status and details
    """
    results = {
        "success": False,
        "messages": [],
        "files_migrated": 0,
        "backup_location": None
    }
    
    try:
        # Don't migrate if directories are the same
        if old_dir.resolve() == new_dir.resolve():
            results["messages"].append("Source and destination are the same")
            results["success"] = True
            return results
        
        # Don't migrate if old directory doesn't exist
        if not old_dir.exists():
            results["messages"].append(f"Source directory does not exist: {old_dir}")
            results["success"] = True  # Nothing to migrate
            return results
        
        # Initialize new directory
        if not initialize_storage_directory(new_dir):
            results["messages"].append("Failed to initialize new storage directory")
            return results
        
        # Create backup of new directory if it has content
        if list(new_dir.glob("*")):
            backup_dir = new_dir.parent / f"{new_dir.name}_backup_{int(datetime.now().timestamp())}"
            try:
                shutil.copytree(str(new_dir), str(backup_dir))
                results["backup_location"] = str(backup_dir)
                results["messages"].append(f"Backup created at {backup_dir}")
            except Exception as e:
                results["messages"].append(f"Warning: Could not create backup: {e}")
        
        # Migrate files and directories
        files_to_migrate = [
            "kanoonvault.db",
            "kanoonvault.db-shm",
            "kanoonvault.db-wal",
            "uploads",
            "chroma_db",
            ".env"
        ]
        
        for item in files_to_migrate:
            old_path = old_dir / item
            new_path = new_dir / item
            
            if not old_path.exists():
                continue
            
            try:
                if old_path.is_file():
                    # Skip if file already exists in new location
                    if not new_path.exists():
                        shutil.copy2(str(old_path), str(new_path))
                        results["files_migrated"] += 1
                        results["messages"].append(f"Migrated file: {item}")
                elif old_path.is_dir():
                    # Merge directories (don't overwrite)
                    if new_path.exists():
                        # Merge subdirectories
                        for subitem in old_path.rglob("*"):
                            rel_path = subitem.relative_to(old_path)
                            new_subitem = new_path / rel_path
                            
                            if subitem.is_file() and not new_subitem.exists():
                                new_subitem.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(str(subitem), str(new_subitem))
                                results["files_migrated"] += 1
                    else:
                        shutil.copytree(str(old_path), str(new_path))
                        results["files_migrated"] += 1
                        results["messages"].append(f"Migrated directory: {item}")
            except Exception as e:
                results["messages"].append(f"Error migrating {item}: {e}")
        
        results["success"] = True
        results["messages"].append("Migration completed successfully")
        
    except Exception as e:
        results["messages"].append(f"Migration failed: {e}")
        results["success"] = False
    
    return results


def get_storage_info(storage_dir: Path) -> dict:
    """
    Get information about storage directory.
    
    Args:
        storage_dir: Path to check
        
    Returns:
        dict with storage info (size, file counts, etc.)
    """
    info = {
        "path": str(storage_dir),
        "exists": storage_dir.exists(),
        "is_writable": os.access(str(storage_dir), os.W_OK) if storage_dir.exists() else None,
        "total_size_mb": 0,
        "file_counts": {
            "total": 0,
            "documents": 0,
            "database": 0,
            "embeddings": 0
        }
    }
    
    if not storage_dir.exists():
        return info
    
    total_size = 0
    total_files = 0
    
    try:
        for root, dirs, files in os.walk(str(storage_dir)):
            for file in files:
                total_files += 1
                file_path = Path(root) / file
                total_size += file_path.stat().st_size
                
                # Categorize files
                if file.endswith(".db") or file.endswith(".db-shm") or file.endswith(".db-wal"):
                    info["file_counts"]["database"] += 1
                elif "uploads" in root:
                    info["file_counts"]["documents"] += 1
                elif "chroma_db" in root:
                    info["file_counts"]["embeddings"] += 1
        
        info["total_size_mb"] = round(total_size / (1024 * 1024), 2)
        info["file_counts"]["total"] = total_files
    except Exception as e:
        print(f"[Storage] Error getting storage info: {e}")
    
    return info


def get_available_disk_space(path: Path) -> dict:
    """
    Get available disk space for a given path.
    
    Args:
        path: Path to check disk space for
        
    Returns:
        dict with disk space info in MB and GB
    """
    try:
        import shutil
        usage = shutil.disk_usage(str(path.parent))
        return {
            "free_mb": round(usage.free / (1024 * 1024), 2),
            "free_gb": round(usage.free / (1024 * 1024 * 1024), 2),
            "total_mb": round(usage.total / (1024 * 1024), 2),
            "total_gb": round(usage.total / (1024 * 1024 * 1024), 2),
        }
    except Exception as e:
        print(f"[Storage] Error getting disk space: {e}")
        return {
            "free_mb": None,
            "free_gb": None,
            "total_mb": None,
            "total_gb": None,
        }


def validate_storage_path(path: Path) -> dict:
    """
    Validate that a path is suitable for storage.
    
    Args:
        path: Path to validate
        
    Returns:
        dict with validation status and any errors
    """
    validation = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Check if path is absolute
        if not path.is_absolute():
            validation["errors"].append("Path must be absolute")
            validation["valid"] = False
        
        # Check if parent directory exists or can be created
        if not path.parent.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                validation["errors"].append(f"Cannot access parent directory: {e}")
                validation["valid"] = False
        
        # Check write permissions
        if path.exists():
            if not os.access(str(path), os.W_OK):
                validation["errors"].append("Directory is not writable")
                validation["valid"] = False
        else:
            if not os.access(str(path.parent), os.W_OK):
                validation["errors"].append("Parent directory is not writable")
                validation["valid"] = False
        
        # Warn about Program Files
        if "program files" in str(path).lower():
            validation["warnings"].append("Using Program Files is not recommended")
        
        # Warn about network drives
        if str(path).startswith("\\\\"):
            validation["warnings"].append("Network drives may have performance issues")
        
    except Exception as e:
        validation["errors"].append(f"Error validating path: {e}")
        validation["valid"] = False
    
    return validation
