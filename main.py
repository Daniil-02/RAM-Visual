import sys
import os
import urllib.request
import zipfile
import io
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.overlay import OverlayWindow
from core.monitor import SystemMonitor
from core.hotkeys import HotkeyListener

class AppManager:
    def __init__(self):
        self.app = QApplication(sys.argv)
        # Предотвращаем закрытие приложения при скрытии главного окна
        self.app.setQuitOnLastWindowClosed(False) 
        
        self.load_styles()
        
        self.monitor = None
        self.overlay = None
        self.hotkey_listener = None
        self.last_overlay_pos = None
        
        self.main_window = MainWindow(self.on_process_selected)
        self.main_window.toggle_overlay_requested.connect(self.toggle_overlay)
        self.main_window.quit_requested.connect(self.force_quit)
        self.main_window.ping_toggled.connect(self.on_ping_toggled)
        self.main_window.show()
        
    def load_styles(self):
        style_path = os.path.join(os.path.dirname(__file__), 'styles', 'theme.qss')
        if os.path.exists(style_path):
            with open(style_path, 'r', encoding='utf-8') as f:
                self.app.setStyleSheet(f.read())
                
    def on_process_selected(self, pid, name):
        # Останавливаем предыдущий мониторинг, если был
        if self.monitor:
            self.monitor.stop()
            
        # Останавливаем предыдущие хоткеи
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            
        # Обновляем оверлей
        if self.overlay:
            self.overlay.close()
            
        self.overlay = OverlayWindow(name)
        self.overlay.request_exit.connect(self.force_quit)
        self.overlay.request_return.connect(self.return_to_main)
        
        # Если позиция была сохранена ранее, восстанавливаем её
        if self.last_overlay_pos is not None:
            self.overlay.move(self.last_overlay_pos)
            

        self.overlay.show()
        self.overlay.toggle_ping_visibility(self.main_window.is_ping_enabled())
        
        # Запускаем сборщик метрик
        self.monitor = SystemMonitor(pid)
        self.monitor.set_ping_enabled(self.main_window.is_ping_enabled())
        self.monitor.metrics_updated.connect(self.overlay.update_metrics)
        self.monitor.start()
        
        # Запускаем перехват горячих клавиш
        self.hotkey_listener = HotkeyListener("alt+f10")
        self.hotkey_listener.toggle_overlay.connect(self.toggle_overlay)
        self.hotkey_listener.start()
        
    def toggle_overlay(self):
        if self.overlay:
            if self.overlay.isVisible():
                self.overlay.hide()
                if self.monitor:
                    self.monitor.pause()
            else:
                self.overlay.show()
                if self.monitor:
                    self.monitor.resume()

    def on_ping_toggled(self, is_enabled):
        if self.overlay:
            self.overlay.toggle_ping_visibility(is_enabled)
        if self.monitor:
            self.monitor.set_ping_enabled(is_enabled)

    def return_to_main(self):
        # Останавливаем мониторинг и хоткеи, закрываем оверлей
        if self.monitor:
            self.monitor.stop()
            self.monitor = None
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener.wait()
            self.hotkey_listener = None
        if self.overlay:
            # Сохраняем текущие координаты оверлея перед его закрытием
            self.last_overlay_pos = self.overlay.pos()
            self.overlay.close()
            self.overlay = None
            
        # Обновляем список и возвращаем главное окно
        self.main_window.load_processes()
        self.main_window.show()

    def force_quit(self):
        if self.monitor:
            self.monitor.stop()
            self.monitor.wait() # Строго дожидаемся завершения потока
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener.wait()
        if self.overlay:
            self.overlay.close()
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())

def ensure_hardware_monitor_dll():
    dll_path = os.path.join(os.path.dirname(__file__), 'LibreHardwareMonitorLib.dll')
    if not os.path.exists(dll_path):
        print("Скачивание LibreHardwareMonitorLib.dll...")
        try:
            url = 'https://www.nuget.org/api/v2/package/LibreHardwareMonitorLib/0.9.3'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=15)
            z = zipfile.ZipFile(io.BytesIO(resp.read()))
            dll_zip_path = [n for n in z.namelist() if n.endswith('LibreHardwareMonitorLib.dll')][0]
            with open(dll_path, 'wb') as f:
                f.write(z.read(dll_zip_path))
            print("Библиотека успешно скачана!")
        except Exception as e:
            print(f"Ошибка при скачивании библиотеки: {e}")

if __name__ == "__main__":
    manager = AppManager()
    
    ensure_hardware_monitor_dll()
    manager.run()
