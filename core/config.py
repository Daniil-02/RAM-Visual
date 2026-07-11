import json
import os

DEFAULT_CONFIG = {
    "hotkey": "alt+f10",
    "opacity": 1.0,
    "ping_enabled": True,
    "is_pinned": False,
    "window_x": None,
    "window_y": None
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

def load_config():
    """Загрузка пользовательских настроек из JSON-файла."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                # Объединяем с дефолтами, чтобы новые ключи подхватывались автоматически
                config = DEFAULT_CONFIG.copy()
                config.update(saved)
                return config
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Сохранение пользовательских настроек в JSON-файл."""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка сохранения конфигурации: {e}")
