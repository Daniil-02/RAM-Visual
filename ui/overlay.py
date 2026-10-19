from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QMenu, QInputDialog, QSlider, QWidgetAction, QPushButton
from PyQt6.QtGui import QAction, QFont, QGuiApplication
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty

class HoverContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.action = None
        self.menu = None

    def enterEvent(self, event):
        if self.menu and self.action:
            self.menu.setActiveAction(self.action)
        super().enterEvent(event)

TRANSLATIONS = {
    "uk": {
        "menu_return": "Повернутися",
        "menu_pin": "Закріпити",
        "menu_unpin": "Відкріпити",
        "menu_opacity": "Прозорість:",
        "menu_hotkey": "Змінити гарячу клавішу...",
        "menu_exit": "Закрити програму",
        "menu_network_mbps": "Перемкнути на Мбіт/с",
        "menu_network_mb": "Перемкнути на Мбайт/с",
        "dialog_hotkey_title": "Змінити гарячу клавішу",
        "dialog_hotkey_text": "Введіть нову комбінацію клавіш\n(наприклад: alt+f10, ctrl+shift+o):",
        "sleep": "Спить",
        "ram": "RAM",
        "cpu": "CPU",
        "gpu": "GPU",
        "ping": "PING"
    },
    "en": {
        "menu_return": "Return",
        "menu_pin": "Pin",
        "menu_unpin": "Unpin",
        "menu_opacity": "Opacity:",
        "menu_hotkey": "Change Hotkey...",
        "menu_exit": "Exit Application",
        "menu_network_mbps": "Switch to Mbps",
        "menu_network_mb": "Switch to MB/s",
        "dialog_hotkey_title": "Change Hotkey",
        "dialog_hotkey_text": "Enter new key combination\n(e.g.: alt+f10, ctrl+shift+o):",
        "sleep": "Sleep",
        "ram": "RAM",
        "cpu": "CPU",
        "gpu": "GPU",
        "ping": "PING"
    }
}

class OverlayWindow(QWidget):
    request_exit = pyqtSignal()
    request_return = pyqtSignal()
    opacity_changed = pyqtSignal(float)
    hotkey_change_requested = pyqtSignal(str)
    pin_toggled = pyqtSignal(bool)
    position_changed = pyqtSignal(int, int)
    mbps_toggled = pyqtSignal(bool)
    
    def get_current_height(self):
        return self.height()
        
    def set_current_height(self, height):
        self.setFixedHeight(height)
        
    current_height = pyqtProperty(int, fget=get_current_height, fset=set_current_height)

    def __init__(self, process_name, config):
        super().__init__()
        self.process_name = process_name
        self.config = config if isinstance(config, dict) else {}
        
        # Verify and clamp opacity between 0.2 and 1.0 (never 0.0)
        raw_opacity = self.config.get("opacity", 1.0)
        try:
            opacity = float(raw_opacity)
        except (ValueError, TypeError):
            opacity = 1.0
        self.initial_opacity = max(0.2, min(1.0, opacity))
        self.config["opacity"] = self.initial_opacity
        self.setWindowOpacity(self.initial_opacity)
        
        self.init_ui()
        self.drag_offset = None
        self.is_pinned = self.config.get("is_pinned", False)
        self.use_mbps = self.config.get("use_mbps", False)
        self.restore_position()

    def apply_safe_font(self):
        """Ensure all fonts have a valid positive point size (> 0) to avoid QFont::setPointSize warnings."""
        configured_font_size = self.config.get("font_size", 10)
        try:
            pt_size = int(configured_font_size)
        except (ValueError, TypeError):
            pt_size = 10
        safe_size = max(9, pt_size)
        
        win_font = self.font()
        win_pt = win_font.pointSize()
        win_font.setPointSize(max(9, win_pt if win_pt > 0 else safe_size))
        self.setFont(win_font)
        
        if hasattr(self, "lbl_name"):
            self.lbl_name.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            for val_lbl in (self.lbl_ram_val, self.lbl_cpu_val, self.lbl_gpu_val, self.lbl_ping_val):
                val_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            for title_lbl in (self.lbl_ram_title, self.lbl_cpu_title, self.lbl_gpu_title, self.lbl_ping_title):
                title_lbl.setFont(QFont("Segoe UI", 9))

    def restore_position(self):
        """Ensure window position is within visible primary screen bounds with safe fallback."""
        primary_screen = QGuiApplication.primaryScreen()
        screen_rect = primary_screen.availableGeometry() if primary_screen else None
        
        self.adjustSize()
        w = max(self.width(), 250)
        
        if screen_rect:
            default_x = screen_rect.x() + screen_rect.width() - w - 20
            default_y = screen_rect.y() + 20
        else:
            default_x = 20
            default_y = 20
            
        wx = self.config.get("window_x")
        wy = self.config.get("window_y")
        
        is_valid = False
        if wx is not None and wy is not None:
            try:
                wx = int(wx)
                wy = int(wy)
                if screen_rect:
                    # Valid if coordinates are not negative and window is visible on screen
                    if (screen_rect.x() <= wx <= screen_rect.x() + screen_rect.width() - 40 and
                        screen_rect.y() <= wy <= screen_rect.y() + screen_rect.height() - 40 and
                        wx >= 0 and wy >= 0):
                        is_valid = True
                elif wx >= 0 and wy >= 0:
                    is_valid = True
            except (ValueError, TypeError):
                is_valid = False
                
        if is_valid:
            self.move(wx, wy)
        else:
            self.move(default_x, default_y)
            self.config["window_x"] = default_x
            self.config["window_y"] = default_y

    def init_ui(self):
        self.setObjectName("OverlayWindow")
        # Frameless window, stays on top of all windows
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        # Transparent background of the main window
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Container for styling (rounded corners and dark semi-transparent background)
        self.container = QFrame(self)
        self.container.setObjectName("OverlayWidget")
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Process name
        display_name = self.process_name
        if display_name.lower().endswith('.exe'):
            display_name = display_name[:-4]
        self.lbl_name = QLabel(display_name)
        self.lbl_name.setObjectName("ProcessNameLabel")
        layout.addWidget(self.lbl_name)
        
        metrics_layout = QVBoxLayout()
        
        # RAM
        self.lbl_ram_val = QLabel("0 MB")
        self.lbl_ram_val.setProperty("class", "MetricValue")
        self.lbl_ram_title = QLabel("RAM")
        self.lbl_ram_title.setProperty("class", "MetricLabel")
        
        row_ram = QHBoxLayout()
        row_ram.addWidget(self.lbl_ram_title)
        row_ram.addStretch()
        row_ram.addWidget(self.lbl_ram_val)
        metrics_layout.addLayout(row_ram)
        
        # CPU
        self.lbl_cpu_val = QLabel("0.0 %")
        self.lbl_cpu_val.setProperty("class", "MetricValue")
        self.lbl_cpu_title = QLabel("CPU")
        self.lbl_cpu_title.setProperty("class", "MetricLabel")
        
        row_cpu = QHBoxLayout()
        row_cpu.addWidget(self.lbl_cpu_title)
        row_cpu.addStretch()
        row_cpu.addWidget(self.lbl_cpu_val)
        metrics_layout.addLayout(row_cpu)
        
        # GPU
        self.lbl_gpu_val = QLabel("0.0 %")
        self.lbl_gpu_val.setProperty("class", "MetricValue")
        self.lbl_gpu_title = QLabel("GPU")
        self.lbl_gpu_title.setProperty("class", "MetricLabel")
        
        row_gpu = QHBoxLayout()
        row_gpu.addWidget(self.lbl_gpu_title)
        row_gpu.addStretch()
        row_gpu.addWidget(self.lbl_gpu_val)
        metrics_layout.addLayout(row_gpu)

        # PING
        self.ping_widget = QWidget()
        self.row_ping = QHBoxLayout(self.ping_widget)
        self.row_ping.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_ping_val = QLabel("---")
        self.lbl_ping_val.setProperty("class", "MetricValue")
        self.lbl_ping_val.setStyleSheet("color: #00E676; font-weight: bold;")
        self.lbl_ping_title = QLabel("PING")
        self.lbl_ping_title.setProperty("class", "MetricLabel")
        
        self.row_ping.addWidget(self.lbl_ping_title)
        self.row_ping.addStretch()
        self.row_ping.addWidget(self.lbl_ping_val)
        metrics_layout.addWidget(self.ping_widget)


        layout.addLayout(metrics_layout)
        main_layout.addWidget(self.container)
        
        self._ping_visible = True
        self.setMinimumWidth(250)
        self.adjustSize()
        self.setFixedHeight(self.height())
        self.apply_safe_font()
        self.retranslate_ui()

    def showEvent(self, event):
        self.retranslate_ui()
        super().showEvent(event)

    def retranslate_ui(self):
        lang = self.config.get("language", "uk")
        t = TRANSLATIONS.get(lang, TRANSLATIONS["uk"])
        self.lbl_ram_title.setText(t["ram"])
        self.lbl_cpu_title.setText(t["cpu"])
        self.lbl_gpu_title.setText(t["gpu"])
        self.lbl_ping_title.setText(t["ping"])

    def update_metrics(self, metrics):
        def update_label_style(label, color_style):
            label.setStyleSheet(color_style)
            label.style().unpolish(label)
            label.style().polish(label)
            label.update()

        ram_mb = metrics['ram']
        self.lbl_ram_val.setText(f"{ram_mb:,.0f} MB".replace(",", " "))
        
        if ram_mb >= 3500:
            update_label_style(self.lbl_ram_val, "color: #FF2A4B; font-weight: bold;")  # Critical Red
        elif ram_mb >= 3000:
            update_label_style(self.lbl_ram_val, "color: #FFC107; font-weight: bold;")  # Warning Yellow
        else:
            update_label_style(self.lbl_ram_val, "color: #00E676; font-weight: bold;")  # Normal Green
        
        cpu_temp = metrics.get('cpu_temp')
        cpu_power = metrics.get('cpu_power')
        cpu_temp_str = f"({cpu_temp:.0f}°C)" if cpu_temp is not None else "(N/A °C)"
        cpu_power_str = f" {cpu_power:.0f}W" if cpu_power is not None else ""
        self.lbl_cpu_val.setText(f"{metrics['cpu']:.1f} %  {cpu_temp_str}{cpu_power_str}")
        
        if cpu_temp is not None:
            if cpu_temp >= 85:
                update_label_style(self.lbl_cpu_val, "color: #FF1744; font-weight: bold;")  # Critical Red
            elif cpu_temp >= 80:
                update_label_style(self.lbl_cpu_val, "color: #FFD600; font-weight: bold;")  # Warning Yellow
            else:
                update_label_style(self.lbl_cpu_val, "color: #00E676; font-weight: bold;")
        else:
            update_label_style(self.lbl_cpu_val, "color: #00E676; font-weight: bold;")
        
        gpu_val = metrics.get('gpu', 0.0)
        gpu_temp = metrics.get('gpu_temp')
        gpu_power = metrics.get('gpu_power')
        gpu_sleep = metrics.get('gpu_sleep', False)
        
        is_sleep = gpu_sleep or str(gpu_val).strip().lower() == 'sleep'
        if is_sleep:
            lang = self.config.get("language", "uk")
            t = TRANSLATIONS.get(lang, TRANSLATIONS["uk"])
            self.lbl_gpu_val.setText(f"0.0 %  ({t['sleep']})")
            update_label_style(self.lbl_gpu_val, "color: #00E676; font-weight: bold;")
        else:
            gpu_temp_str = f"({gpu_temp:.0f}°C)" if gpu_temp is not None else "(N/A °C)"
            gpu_power_str = f" {gpu_power:.0f}W" if gpu_power is not None else ""
            
            is_na = False
            if isinstance(gpu_val, str) and gpu_val.strip().upper() == "N/A":
                is_na = True
            elif isinstance(gpu_val, (int, float)) and gpu_val < 0:
                is_na = True
                
            if is_na:
                self.lbl_gpu_val.setText(f"N/A  {gpu_temp_str}{gpu_power_str}")
            else:
                try:
                    num_val = float(gpu_val)
                    self.lbl_gpu_val.setText(f"{num_val:.1f} %  {gpu_temp_str}{gpu_power_str}")
                except (ValueError, TypeError):
                    self.lbl_gpu_val.setText(f"{gpu_val}  {gpu_temp_str}{gpu_power_str}")
                
            if gpu_temp is not None:
                if gpu_temp >= 85:
                    update_label_style(self.lbl_gpu_val, "color: #FF1744; font-weight: bold;")  # Critical Red
                elif gpu_temp >= 80:
                    update_label_style(self.lbl_gpu_val, "color: #FFD600; font-weight: bold;")  # Warning Yellow
                else:
                    update_label_style(self.lbl_gpu_val, "color: #00E676; font-weight: bold;")
            else:
                update_label_style(self.lbl_gpu_val, "color: #00E676; font-weight: bold;")
            
        if 'ping' in metrics and self._ping_visible:
            speed = metrics.get('download_speed', 0.0)
            if self.use_mbps:
                speed = speed * 8.0
                unit = "Mbps"
            else:
                unit = "MB/s"
            ping_val = str(metrics['ping'])
            self.lbl_ping_val.setText(f"{ping_val} (↓ {speed:.1f} {unit})")
            
            # Dynamic styling matching MetricValue size and alerts
            ping_ms = None
            if "ms" in ping_val.lower():
                try:
                    num_part = ping_val.lower().replace("ms", "").replace("<", "").strip()
                    ping_ms = float(num_part)
                except ValueError:
                    pass
                    
            if ping_val == "Err" or (ping_ms is not None and ping_ms >= 150):
                update_label_style(self.lbl_ping_val, "color: #FF2A4B; font-weight: bold;")
            elif ping_ms is not None and ping_ms >= 80:
                update_label_style(self.lbl_ping_val, "color: #FFC107; font-weight: bold;")
            else:
                update_label_style(self.lbl_ping_val, "color: #00E676; font-weight: bold;")

    def toggle_ping_visibility(self, visible):
        if hasattr(self, '_ping_visible') and self._ping_visible == visible:
            return
        self._ping_visible = visible
        
        start_height = self.height()
        
        self.ping_widget.setVisible(visible)
        
        # Temporarily remove restrictions so the layout can accurately calculate the required height
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        
        # Force the layout to update calculations
        self.layout().activate()
        target_height = self.layout().sizeHint().height()
        
        # If the window is not on screen yet, just fix the calculated size
        if not self.isVisible():
            self.setFixedHeight(target_height)
            return
            
        if not hasattr(self, 'size_anim'):
            self.size_anim = QPropertyAnimation(self, b"current_height")
            self.size_anim.setDuration(200)
            self.size_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
        self.size_anim.stop()
        self.size_anim.setStartValue(start_height)
        self.size_anim.setEndValue(target_height)
        self.size_anim.start()



    # Window dragging logic (Drag-and-Drop) with magnetic snapping
    def mousePressEvent(self, event):
        if not self.is_pinned and event.button() == Qt.MouseButton.LeftButton:
            # Cursor offset relative to the top-left corner of the window
            self.drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if not self.is_pinned and hasattr(self, 'drag_offset') and self.drag_offset is not None:
            # Ideal theoretical window position (without snapping)
            target_pos = event.globalPosition().toPoint() - self.drag_offset
            new_x = target_pos.x()
            new_y = target_pos.y()
            
            # Available geometry of the current monitor (including taskbar)
            screen = self.screen() or QGuiApplication.primaryScreen()
            if screen:
                screen_geom = screen.availableGeometry()
                snap_margin = 15
                
                # Snapping to left and right edges
                if abs(new_x - screen_geom.left()) <= snap_margin:
                    new_x = screen_geom.left()
                elif abs(new_x + self.width() - screen_geom.right()) <= snap_margin:
                    new_x = screen_geom.right() - self.width() + 1
                    
                # Snapping to top and bottom edges
                if abs(new_y - screen_geom.top()) <= snap_margin:
                    new_y = screen_geom.top()
                elif abs(new_y + self.height() - screen_geom.bottom()) <= snap_margin:
                    new_y = screen_geom.bottom() - self.height() + 1
            
            self.move(new_x, new_y)

    def mouseReleaseEvent(self, event):
        if self.drag_offset is not None:
            self.drag_offset = None
            self.position_changed.emit(self.x(), self.y())

    def contextMenuEvent(self, event):
        lang = self.config.get("language", "uk")
        t = TRANSLATIONS.get(lang, TRANSLATIONS["uk"])
        
        menu = QMenu(self)
        
        # Soft hover effects for the entire context menu
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 122, 255, 0.25); /* Brighter transparent selection */
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: #333333;
                margin: 4px 8px;
            }
        """)
        
        return_action = QAction(t["menu_return"], self)
        return_action.triggered.connect(self.request_return.emit)
        
        pin_text = t["menu_unpin"] if self.is_pinned else t["menu_pin"]
        pin_action = QAction(pin_text, self)
        pin_action.triggered.connect(self.toggle_pin)

        # Integrated opacity slider
        opacity_widget = HoverContainer()
        opacity_widget.menu = menu
        opacity_layout = QHBoxLayout(opacity_widget)
        opacity_layout.setContentsMargins(14, 5, 14, 5)
        opacity_layout.setSpacing(10)
        
        lbl_title = QLabel(t["menu_opacity"])
        lbl_title.setStyleSheet("color: #E0E0E0; background: transparent;")
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimumWidth(180)
        slider.setRange(20, 100)
        
        # Elegant, thin slider design
        slider.setStyleSheet("""
            QSlider {
                background: transparent;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 3px;
                background: #333333;
                border-radius: 1px;
            }
            QSlider::sub-page:horizontal {
                background: #007AFF;
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: none;
                width: 10px;
                margin-top: -3px;
                margin-bottom: -4px;
                border-radius: 5px;
            }
            QSlider::handle:horizontal:hover {
                background: #B3C6FF;
            }
        """)
        
        current_opacity = int(self.windowOpacity() * 100)
        slider.setValue(current_opacity)
        
        lbl_percent = QLabel(f"{current_opacity}%")
        lbl_percent.setStyleSheet("color: #E0E0E0; font-weight: bold; min-width: 35px;")
        lbl_percent.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        opacity_layout.addWidget(lbl_title)
        opacity_layout.addWidget(slider)
        opacity_layout.addWidget(lbl_percent)
        
        def on_slider_moved(val):
            lbl_percent.setText(f"{val}%")
            self.setWindowOpacity(val / 100.0)
            
        slider.valueChanged.connect(on_slider_moved)
        slider.sliderReleased.connect(lambda: self.opacity_changed.emit(slider.value() / 100.0))
        
        slider_action = QWidgetAction(self)
        slider_action.setDefaultWidget(opacity_widget)
        opacity_widget.action = slider_action

        hotkey_action = QAction(t["menu_hotkey"], self)
        hotkey_action.triggered.connect(self._on_hotkey_change)
        
        exit_action = QAction(t["menu_exit"], self)
        exit_action.triggered.connect(self.request_exit.emit)
        
        # Custom button to switch network measurement units
        network_widget = HoverContainer()
        network_widget.menu = menu
        network_layout = QHBoxLayout(network_widget)
        network_layout.setContentsMargins(2, 2, 2, 2)
        
        btn_network = QPushButton()
        btn_network.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_network.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #E0E0E0;
                font-weight: normal;
                border: none;
                text-align: left;
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(0, 122, 255, 0.25);
                color: #FFFFFF;
            }
        """)
        
        def update_network_btn_text():
            if self.use_mbps:
                btn_network.setText(t["menu_network_mb"])
            else:
                btn_network.setText(t["menu_network_mbps"])
                
        update_network_btn_text()
        
        def on_network_clicked():
            self.toggle_mbps(not self.use_mbps)
            update_network_btn_text()
            
        btn_network.clicked.connect(on_network_clicked)
        network_layout.addWidget(btn_network)
        
        network_action = QWidgetAction(self)
        network_action.setDefaultWidget(network_widget)
        network_widget.action = network_action
        
        menu.addAction(return_action)
        menu.addAction(pin_action)
        menu.addAction(network_action)
        menu.addSeparator()
        menu.addAction(slider_action)
        menu.addAction(hotkey_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        
        menu.exec(event.globalPos())

    def _on_hotkey_change(self):
        lang = self.config.get("language", "uk")
        t = TRANSLATIONS.get(lang, TRANSLATIONS["uk"])
        new_hotkey, ok = QInputDialog.getText(
            self, t["dialog_hotkey_title"],
            t["dialog_hotkey_text"],
            text="alt+f10"
        )
        if ok and new_hotkey.strip():
            self.hotkey_change_requested.emit(new_hotkey.strip().lower())

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.pin_toggled.emit(self.is_pinned)

    def toggle_mbps(self, checked):
        self.use_mbps = checked
        self.mbps_toggled.emit(self.use_mbps)
