import keyboard
from PyQt6.QtCore import QThread, pyqtSignal

class HotkeyListener(QThread):
    toggle_overlay = pyqtSignal()
    
    def __init__(self, hotkey="alt+f10"):
        super().__init__()
        self.hotkey = hotkey
        self.running = True
        
    def run(self):
        # Регистрируем глобальный хук
        try:
            keyboard.add_hotkey(self.hotkey, self._on_hotkey)
        except Exception as e:
            print(f"Ошибка регистрации хоткея: {e}")
            
        # Держим поток активным
        while self.running:
            self.msleep(200) # Проверяем каждые 200 мс флаг завершения
            
    def _on_hotkey(self):
        self.toggle_overlay.emit()
        
    def stop(self):
        self.running = False
        try:
            keyboard.remove_hotkey(self.hotkey)
        except Exception:
            pass
        self.wait()
