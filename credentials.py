"""
Windows Credential Manager Integration for KanoonVault

Provides secure storage of API keys using Windows DPAPI (Data Protection API)
via the credential manager, avoiding plain-text storage.

On non-Windows systems or when keyring is not installed, falls back to .env file storage.
"""

import os
import sys
import json
from pathlib import Path

# ── Optional keyring import ────────────────────────────────────────────────
KEYRING_AVAILABLE = False
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    pass


def get_credential_service_name() -> str:
    """Get the service name for credential storage."""
    return "KanoonVault"


def save_api_key(key_type: str, api_key: str) -> bool:
    """
    Save an API key securely using the system credential manager.
    Falls back to .env file if keyring is not available.
    """
    if KEYRING_AVAILABLE:
        try:
            service = get_credential_service_name()
            keyring.set_password(service, key_type, api_key)
            return True
        except Exception as e:
            print(f"[WARN] Failed to save API key to credential manager: {e}")

    # Fall back to .env file
    return _save_key_to_env_file(key_type, api_key)


def load_api_key(key_type: str) -> str | None:
    """
    Load an API key from secure storage.
    Falls back to .env file if keyring is not available.
    """
    if KEYRING_AVAILABLE:
        try:
            service = get_credential_service_name()
            key = keyring.get_password(service, key_type)
            if key:
                return key
        except Exception as e:
            print(f"[WARN] Failed to load API key from credential manager: {e}")

    # Fall back to .env file
    return _load_key_from_env_file(key_type)


def delete_api_key(key_type: str) -> bool:
    """Delete an API key from secure storage."""
    if KEYRING_AVAILABLE:
        try:
            service = get_credential_service_name()
            keyring.delete_password(service, key_type)
            return True
        except Exception as e:
            print(f"[WARN] Failed to delete API key: {e}")
    return False


def _save_key_to_env_file(key_type: str, api_key: str) -> bool:
    """
    Fallback: Save API key to .env file in user data directory.
    
    This is less secure than credential manager but works on all systems.
    """
    try:
        user_data = os.environ.get("KANOONVAULT_USER_DATA_DIR")
        if user_data:
            env_file = Path(user_data) / ".env"
        else:
            # Dev mode: save to project root .env
            env_file = Path(__file__).parent / ".env"
        
        # Load existing .env content
        env_content = {}
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env_content[k.strip()] = v.strip().strip('"').strip("'")
        
        # Map key_type to environment variable name
        env_key_map = {
            "OPENROUTER": "OPENROUTER_API_KEY",
            "OCR_VISION": "OCR_VISION_API_KEY",
            "TIMELINE": "TIMELINE_API_KEY",
        }
        
        env_var_name = env_key_map.get(key_type, f"{key_type}_API_KEY")
        env_content[env_var_name] = api_key
        
        # Write back to file
        lines = []
        for key, value in env_content.items():
            lines.append(f"{key}={value}")
        
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save to .env file: {e}")
        return False


def _load_key_from_env_file(key_type: str) -> str | None:
    """
    Fallback: Load API key from .env file in user data directory.
    """
    try:
        user_data = os.environ.get("KANOONVAULT_USER_DATA_DIR")
        if user_data:
            env_file = Path(user_data) / ".env"
        else:
            env_file = Path(__file__).parent / ".env"
        
        if not env_file.exists():
            return None
        
        env_key_map = {
            "OPENROUTER": "OPENROUTER_API_KEY",
            "OCR_VISION": "OCR_VISION_API_KEY",
            "TIMELINE": "TIMELINE_API_KEY",
        }
        
        env_var_name = env_key_map.get(key_type, f"{key_type}_API_KEY")
        
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(env_var_name + "="):
                _, _, value = line.partition("=")
                return value.strip().strip('"').strip("'")
        
        return None
    except Exception as e:
        print(f"[WARN] Failed to load from .env file: {e}")
        return None


def is_api_key_configured(key_type: str = "OPENROUTER") -> bool:
    """
    Check if an API key is configured.
    
    Args:
        key_type: Type of key to check
        
    Returns:
        True if the key is configured and non-empty
    """
    key = load_api_key(key_type)
    return bool(key and key.strip())


def get_all_configured_keys() -> dict[str, bool]:
    """
    Get a dictionary of which API keys are configured.
    
    Returns:
        Dict mapping key type to whether it's configured
    """
    return {
        "OPENROUTER": is_api_key_configured("OPENROUTER"),
        "OCR_VISION": is_api_key_configured("OCR_VISION"),
        "TIMELINE": is_api_key_configured("TIMELINE"),
    }
