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
        # Register the global hook
        self._register(self.hotkey)
            
        # Keep the thread active
        while self.running:
            self.msleep(200) # Check the termination flag every 200 ms
            
    def _on_hotkey(self):
        self.toggle_overlay.emit()

    def _register(self, hotkey):
        """Register a new hotkey after safely clearing the old one."""
        self._unregister()
        try:
            self._hook = keyboard.add_hotkey(hotkey, self._on_hotkey)
            self.hotkey = hotkey
            return True
        except Exception as e:
            print(f"Error registering hotkey '{hotkey}': {e}")
            return False

    def _unregister(self):
        """Unregister the current hook if it exists."""
        if self._hook is not None:
            try:
                keyboard.remove_hotkey(self._hook)
            except Exception:
                pass
            self._hook = None

    def rebind(self, new_hotkey):
        """Rebind hotkey on the fly without restarting the thread."""
        return self._register(new_hotkey)

    def stop(self):
        self.running = False
        self._unregister()
        self.wait()
