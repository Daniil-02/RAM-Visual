import json
import os
import sys

DEFAULT_CONFIG = {
    "hotkey": "alt+f10",
    "opacity": 1.0,
    "ping_enabled": True,
    "is_pinned": False,
    "window_x": None,
    "window_y": None,
    "use_mbps": False,
    "language": "uk"
}

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def load_config():
    """Load user configuration from a JSON file."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                # Merge with defaults so new keys are automatically picked up
                config = DEFAULT_CONFIG.copy()
                config.update(saved)
                if config.get("language") not in ("uk", "en"):
                    config["language"] = "uk"
                try:
                    opacity = float(config.get("opacity", 1.0))
                    config["opacity"] = max(0.2, min(1.0, opacity))
                except (ValueError, TypeError):
                    config["opacity"] = 1.0
                return config
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save user configuration to a JSON file."""
    try:
        if config.get("language") not in ("uk", "en"):
            config["language"] = "uk"
        try:
            opacity = float(config.get("opacity", 1.0))
            config["opacity"] = max(0.2, min(1.0, opacity))
        except (ValueError, TypeError):
            config["opacity"] = 1.0
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving configuration: {e}")
