import keyboard
from PyQt6.QtCore import QThread, pyqtSignal

class HotkeyListener(QThread):
    toggle_overlay = pyqtSignal()
    
    def __init__(self, hotkey="alt+f10"):
        super().__init__()
        self.hotkey = hotkey
        self.running = True
        self._hook = None
        
    def run(self):
        # Регистрируем глобальный хук
        self._register(self.hotkey)
            
        # Держим поток активным
        while self.running:
            self.msleep(200) # Проверяем каждые 200 мс флаг завершения
            
    def _on_hotkey(self):
        self.toggle_overlay.emit()

    def _register(self, hotkey):
        """Регистрация нового хоткея с безопасной очисткой старого."""
        self._unregister()
        try:
            self._hook = keyboard.add_hotkey(hotkey, self._on_hotkey)
            self.hotkey = hotkey
            return True
        except Exception as e:
            print(f"Ошибка регистрации хоткея '{hotkey}': {e}")
            return False

    def _unregister(self):
        """Снятие текущего хука, если он существует."""
        if self._hook is not None:
            try:
                keyboard.remove_hotkey(self._hook)
            except Exception:
                pass
            self._hook = None

    def rebind(self, new_hotkey):
        """Переназначение хоткея на лету, без перезапуска потока."""
        return self._register(new_hotkey)

    def stop(self):
        self.running = False
        self._unregister()
        self.wait()
