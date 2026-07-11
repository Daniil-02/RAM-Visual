from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QMenu, QInputDialog
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty

class OverlayWindow(QWidget):
    request_exit = pyqtSignal()
    request_return = pyqtSignal()
    opacity_changed = pyqtSignal(float)
    hotkey_change_requested = pyqtSignal(str)
    
    def get_current_height(self):
        return self.height()
        
    def set_current_height(self, height):
        self.setFixedHeight(height)
        
    current_height = pyqtProperty(int, fget=get_current_height, fset=set_current_height)

    def __init__(self, process_name):
        super().__init__()
        self.process_name = process_name
        self.init_ui()
        self.old_pos = None
        self.is_pinned = False

    def init_ui(self):
        self.setObjectName("OverlayWindow")
        # Без рамок, поверх всех окон
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        # Прозрачный фон основного окна
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Контейнер для стилизации (закругленные углы и темный полупрозрачный фон)
        self.container = QFrame(self)
        self.container.setObjectName("OverlayWidget")
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Название процесса
        self.lbl_name = QLabel(self.process_name)
        self.lbl_name.setObjectName("ProcessNameLabel")
        layout.addWidget(self.lbl_name)
        
        metrics_layout = QVBoxLayout()
        
        # RAM
        self.lbl_ram_val = QLabel("0 MB")
        self.lbl_ram_val.setProperty("class", "MetricValue")
        lbl_ram_title = QLabel("RAM")
        lbl_ram_title.setProperty("class", "MetricLabel")
        
        row_ram = QHBoxLayout()
        row_ram.addWidget(lbl_ram_title)
        row_ram.addStretch()
        row_ram.addWidget(self.lbl_ram_val)
        metrics_layout.addLayout(row_ram)
        
        # CPU
        self.lbl_cpu_val = QLabel("0.0 %")
        self.lbl_cpu_val.setProperty("class", "MetricValue")
        lbl_cpu_title = QLabel("CPU")
        lbl_cpu_title.setProperty("class", "MetricLabel")
        
        row_cpu = QHBoxLayout()
        row_cpu.addWidget(lbl_cpu_title)
        row_cpu.addStretch()
        row_cpu.addWidget(self.lbl_cpu_val)
        metrics_layout.addLayout(row_cpu)
        
        # GPU
        self.lbl_gpu_val = QLabel("0.0 %")
        self.lbl_gpu_val.setProperty("class", "MetricValue")
        lbl_gpu_title = QLabel("GPU")
        lbl_gpu_title.setProperty("class", "MetricLabel")
        
        row_gpu = QHBoxLayout()
        row_gpu.addWidget(lbl_gpu_title)
        row_gpu.addStretch()
        row_gpu.addWidget(self.lbl_gpu_val)
        metrics_layout.addLayout(row_gpu)

        # PING
        self.ping_widget = QWidget()
        self.row_ping = QHBoxLayout(self.ping_widget)
        self.row_ping.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_ping_val = QLabel("---")
        self.lbl_ping_val.setProperty("class", "MetricValue")
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

    def update_metrics(self, metrics):
        self.lbl_ram_val.setText(f"{metrics['ram']:,.0f} MB".replace(",", " "))
        
        cpu_temp = metrics.get('cpu_temp')
        cpu_power = metrics.get('cpu_power')
        cpu_temp_str = f"({cpu_temp:.0f}°C)" if cpu_temp is not None else "(N/A °C)"
        cpu_power_str = f" {cpu_power:.0f}W" if cpu_power is not None else ""
        self.lbl_cpu_val.setText(f"{metrics['cpu']:.1f} %  {cpu_temp_str}{cpu_power_str}")
        
        gpu_val = metrics['gpu']
        gpu_temp = metrics.get('gpu_temp')
        gpu_power = metrics.get('gpu_power')
        gpu_temp_str = f"({gpu_temp:.0f}°C)" if gpu_temp is not None else "(N/A °C)"
        gpu_power_str = f" {gpu_power:.0f}W" if gpu_power is not None else ""
        
        if gpu_val < 0:
            self.lbl_gpu_val.setText(f"N/A  {gpu_temp_str}{gpu_power_str}")
        else:
            self.lbl_gpu_val.setText(f"{gpu_val:.1f} %  {gpu_temp_str}{gpu_power_str}")
            
        if 'ping' in metrics and self._ping_visible:
            speed = metrics.get('download_speed', 0.0)
            self.lbl_ping_val.setText(f"{metrics['ping']} (↓ {speed:.1f} MB/s)")

    def toggle_ping_visibility(self, visible):
        if hasattr(self, '_ping_visible') and self._ping_visible == visible:
            return
        self._ping_visible = visible
        
        start_height = self.height()
        
        self.ping_widget.setVisible(visible)
        
        # Временно снимаем ограничения, чтобы layout мог честно рассчитать требуемую высоту
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        
        # Заставляем макет обновить расчеты
        self.layout().activate()
        target_height = self.layout().sizeHint().height()
        
        # Если окно еще не на экране, просто фиксируем рассчитанный размер
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



    # Логика для перемещения окна (Drag-and-Drop)
    def mousePressEvent(self, event):
        if not self.is_pinned and event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if not self.is_pinned and self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        return_action = QAction("Вернуться", self)
        return_action.triggered.connect(self.request_return.emit)
        
        pin_text = "Открепить" if self.is_pinned else "Закрепить"
        pin_action = QAction(pin_text, self)
        pin_action.triggered.connect(self.toggle_pin)

        opacity_menu = QMenu("Прозрачность", self)
        opacity_group = QActionGroup(self)
        opacity_group.setExclusive(True)
        current_opacity = self.windowOpacity()
        
        for label, value in [("100%", 1.0), ("80%", 0.8), ("60%", 0.6), ("40%", 0.4)]:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setData(value)
            if abs(current_opacity - value) < 0.01:
                action.setChecked(True)
            opacity_group.addAction(action)
            opacity_menu.addAction(action)
            
        opacity_group.triggered.connect(lambda action: self.opacity_changed.emit(action.data()))

        hotkey_action = QAction("Сменить хоткей...", self)
        hotkey_action.triggered.connect(self._on_hotkey_change)
        
        exit_action = QAction("Закрыть приложение", self)
        exit_action.triggered.connect(self.request_exit.emit)
        
        menu.addAction(return_action)
        menu.addAction(pin_action)
        menu.addSeparator()
        menu.addMenu(opacity_menu)
        menu.addAction(hotkey_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        
        menu.exec(event.globalPos())

    def _on_hotkey_change(self):
        new_hotkey, ok = QInputDialog.getText(
            self, "Сменить хоткей",
            "Введите новую комбинацию клавиш\n(например: alt+f10, ctrl+shift+o):",
            text="alt+f10"
        )
        if ok and new_hotkey.strip():
            self.hotkey_change_requested.emit(new_hotkey.strip().lower())

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
