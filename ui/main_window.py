import psutil
import win32gui
import win32process
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QLineEdit, QPushButton, QLabel,
                             QSystemTrayIcon, QMenu, QFrame, QCheckBox)
from PyQt6.QtCore import Qt, QSize, QFileInfo, pyqtSignal, QVariantAnimation
from PyQt6.QtGui import QIcon, QAction, QColor, QPalette, QCloseEvent
from PyQt6.QtWidgets import QFileIconProvider
from core.config import save_config

def get_visible_windows_pids():
    """Получает множество PID процессов, имеющих видимые окна на рабочем столе."""
    visible_pids = set()
    def enum_windows_proc(hwnd, lParam):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            visible_pids.add(pid)
        return True
    try:
        win32gui.EnumWindows(enum_windows_proc, 0)
    except Exception:
        pass
    return visible_pids

class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bg_color = QColor("#2962FF")
        
        self.bg_anim = QVariantAnimation(self)
        self.bg_anim.setDuration(200)
        self.bg_anim.valueChanged.connect(self._update_bg_color)
        
        self._apply_style()
        
    def _update_bg_color(self, color):
        self._bg_color = color
        self._apply_style()
        
    def _apply_style(self):
        self.setStyleSheet(f"AnimatedButton {{ background-color: {self._bg_color.name()}; color: white; border: none; border-radius: 5px; padding: 10px; font-weight: bold; }}")

    def enterEvent(self, event):
        self.bg_anim.stop()
        self.bg_anim.setStartValue(self._bg_color)
        self.bg_anim.setEndValue(QColor("#1C44B2"))
        self.bg_anim.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.bg_anim.stop()
        self.bg_anim.setStartValue(self._bg_color)
        self.bg_anim.setEndValue(QColor("#2962FF"))
        self.bg_anim.start()
        super().leaveEvent(event)

class ProcessItemWidget(QFrame):
    def __init__(self, name, pid, icon, parent=None):
        super().__init__(parent)
        self.pid = pid
        self.name = name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        self.icon_label = QLabel()
        if not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(24, 24))
        
        self.text_label = QLabel(name)
        self.text_label.setStyleSheet("color: #E0E0E0; font-size: 14px; background: transparent; border: none;")
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()
        
        self._bg_alpha = 0.0
        self._apply_style()
        
        self.bg_anim = QVariantAnimation(self)
        self.bg_anim.setDuration(250)
        self.bg_anim.valueChanged.connect(self._update_bg_alpha)

    def _update_bg_alpha(self, alpha):
        self._bg_alpha = alpha
        self._apply_style()
        
    def _apply_style(self):
        # В CSS параметр alpha для rgba() ожидается в диапазоне 0.0 - 1.0 (float)
        self.setStyleSheet(f"ProcessItemWidget {{ background-color: rgba(255, 255, 255, {self._bg_alpha:.3f}); border-radius: 5px; border-bottom: 1px solid #2C2C2C; }}")

    def enterEvent(self, event):
        self.bg_anim.stop()
        self.bg_anim.setStartValue(self._bg_alpha)
        self.bg_anim.setEndValue(0.06) # Мягкий, полупрозрачный белый фон
        self.bg_anim.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.bg_anim.stop()
        self.bg_anim.setStartValue(self._bg_alpha)
        self.bg_anim.setEndValue(0.0) # Полностью прозрачный
        self.bg_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            list_widget = self.parent().parent()
            if isinstance(list_widget, QListWidget):
                for i in range(list_widget.count()):
                    item = list_widget.item(i)
                    if list_widget.itemWidget(item) == self:
                        list_widget.setCurrentItem(item)
                        break
        super().mousePressEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        main_win = self.window()
        if hasattr(main_win, 'select_process'):
            main_win.select_process()

TRANSLATIONS = {
    "ru": {
        "window_title": "RAM Visual - Выбор процесса",
        "header": "Выберите приложение для мониторинга",
        "search_placeholder": "Поиск процесса...",
        "btn_refresh": "Обновить список",
        "btn_monitor": "Мониторить",
        "flag_btn": "🌐 RU",
        "tray_toggle": "Показать/Скрыть оверлей",
        "tray_ping": "Показывать Ping",
        "tray_quit": "Выход"
    },
    "en": {
        "window_title": "RAM Visual - Process Selection",
        "header": "Select an application to monitor",
        "search_placeholder": "Search process...",
        "btn_refresh": "Refresh List",
        "btn_monitor": "Monitor",
        "flag_btn": "🌐 EN",
        "tray_toggle": "Show/Hide Overlay",
        "tray_ping": "Show Ping",
        "tray_quit": "Exit"
    }
}

class MainWindow(QMainWindow):
    toggle_overlay_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    ping_toggled = pyqtSignal(bool)
    
    def __init__(self, on_process_selected, config):
        super().__init__()
        self.on_process_selected = on_process_selected
        self.config = config
        self.init_ui()
        self.init_tray()
        self.load_processes()
        
    def init_ui(self):
        self.setObjectName("MainWindow")
        self.resize(450, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        top_layout = QHBoxLayout()
        self.lbl_header = QLabel()
        self.lbl_header.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        self.btn_lang = QPushButton()
        self.btn_lang.setObjectName("LangBtn")
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.setFixedWidth(80)
        self.btn_lang.setStyleSheet("""
            QPushButton#LangBtn {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: #A0A0A0;
                font-family: "Segoe UI Emoji", "Segoe UI", sans-serif;
                font-size: 13px;
                font-weight: 600;
                padding: 4px 8px;
            }
            QPushButton#LangBtn:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
            }
            QPushButton#LangBtn:pressed {
                background-color: rgba(255, 255, 255, 0.03);
                color: #D0D0D0;
            }
        """)
        self.btn_lang.clicked.connect(self.toggle_language)
        
        top_layout.addWidget(self.lbl_header)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_lang)
        layout.addLayout(top_layout)
        
        self.search_box = QLineEdit()
        self.search_box.textChanged.connect(self.filter_processes)
        layout.addWidget(self.search_box)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget::item { padding: 0px; }")
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        self.btn_refresh = AnimatedButton("")
        self.btn_refresh.clicked.connect(self.load_processes)
        
        self.btn_select = AnimatedButton("")
        self.btn_select.clicked.connect(self.select_process)
        
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_select)
        layout.addLayout(btn_layout)
        
        self.retranslate_ui()

    def toggle_language(self):
        current_lang = self.config.get("language", "ru")
        new_lang = "en" if current_lang == "ru" else "ru"
        self.config["language"] = new_lang
        save_config(self.config)
        self.retranslate_ui()

    def retranslate_ui(self):
        lang = self.config.get("language", "ru")
        translations = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
        
        self.setWindowTitle(translations["window_title"])
        self.lbl_header.setText(translations["header"])
        self.search_box.setPlaceholderText(translations["search_placeholder"])
        self.btn_refresh.setText(translations["btn_refresh"])
        self.btn_select.setText(translations["btn_monitor"])
        self.btn_lang.setText(translations["flag_btn"])
        
        if hasattr(self, 'tray_toggle_action'):
            self.tray_toggle_action.setText(translations["tray_toggle"])
            self.ping_action.setText(translations["tray_ping"])
            self.tray_quit_action.setText(translations["tray_quit"])

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("RAM-Visuals")
        
        provider = QFileIconProvider()
        icon = provider.icon(QFileIconProvider.IconType.Computer)
        self.tray_icon.setIcon(icon)
        
        tray_menu = QMenu()
        
        self.tray_toggle_action = QAction("Показать/Скрыть оверлей", self)
        self.tray_toggle_action.triggered.connect(self.toggle_overlay_requested.emit)
        
        self.ping_action = QAction("Показывать Ping", self)
        self.ping_action.setCheckable(True)
        self.ping_action.setChecked(True)
        self.ping_action.triggered.connect(self.ping_toggled.emit)

        self.tray_quit_action = QAction("Выход", self)
        self.tray_quit_action.triggered.connect(self.quit_requested.emit)
        
        tray_menu.addAction(self.tray_toggle_action)
        tray_menu.addAction(self.ping_action)
        tray_menu.addSeparator()
        tray_menu.addAction(self.tray_quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_overlay_requested.emit()

    def closeEvent(self, event: QCloseEvent):
        # Ранее здесь было сворачивание в системный трей (event.ignore() и self.hide()).
        # По вашей новой просьбе, нажатие "крестика" теперь вызывает полное и чистое 
        # завершение программы с остановкой всех потоков мониторинга.
        self.quit_requested.emit()
        event.accept()

    def force_quit(self):
        self.quit_requested.emit()

    def is_ping_enabled(self):
        return self.ping_action.isChecked()

    def set_ping_from_config(self, enabled):
        """Устанавливает состояние чекбокса пинга из конфига."""
        self.ping_action.setChecked(enabled)

    def load_processes(self):
        self.list_widget.clear()
        provider = QFileIconProvider()
        
        # Получаем PID только приложений с видимыми графическими окнами
        visible_pids = get_visible_windows_pids()
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                info = proc.info
                # Фильтруем: оставляем только те процессы, которые имеют видимые окна
                if info['pid'] in visible_pids and info['name'] and info['exe']:
                    processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        processes.sort(key=lambda x: x['name'].lower())
        
        seen_paths = set()
        for p in processes:
            path = p['exe']
            if path not in seen_paths:
                seen_paths.add(path)
                icon = QIcon()
                try:
                    icon = provider.icon(QFileInfo(path))
                except Exception:
                    pass
                    
                item = QListWidgetItem(self.list_widget)
                item.setData(Qt.ItemDataRole.UserRole, p)
                item.setSizeHint(QSize(0, 48))
                
                widget = ProcessItemWidget(p['name'], p['pid'], icon)
                self.list_widget.setItemWidget(item, widget)

    def filter_processes(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                item.setHidden(text.lower() not in widget.name.lower())

    def select_process(self, item=None):
        # Если метод вызван от клика кнопки, 'item' будет Boolean. Исправляем этот баг:
        if not isinstance(item, QListWidgetItem):
            item = self.list_widget.currentItem()
            
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            self.on_process_selected(data['pid'], data['name'])
            self.hide()
