import sys
import os
import psutil
import pynvml
from PyQt5 import QtWidgets, QtGui, QtCore

class TrayAnimator(QtWidgets.QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.metric = 'cpu'     # or 'gpu'
        self.theme = 'dark'     # or 'light'
        self.base_path = 'resources'
        self.frame_index = 0
        self.icons = []

        try:
            pynvml.nvmlInit()
            self.nvml_available = True
        except:
            self.nvml_available = False

        self.reload_icons()
        self.setIcon(self.icons[0])
        self.setToolTip("RunnerCat – System Tray Monitor")

        self.metric_timer = QtCore.QTimer()
        self.metric_timer.timeout.connect(self.update_metrics)
        self.metric_timer.start(1000)

        self.anim_timer = QtCore.QTimer()
        self.anim_timer.timeout.connect(self.animate_icon)
        self.anim_timer.start(800)

        self.menu = QtWidgets.QMenu()
        self.setContextMenu(self.menu)
        self.activated.connect(self.handle_click)

        self.update_metrics()
        self.show()

    def get_resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def reload_icons(self):
        folder = self.get_resource_path(os.path.join(self.base_path, self.metric))
        prefix = f"{self.theme}_{'cat' if self.metric == 'cpu' else 'horse'}"
        files = sorted(f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith('.ico'))
        self.icons = [QtGui.QIcon(os.path.join(folder, f)) for f in files]
        self.frame_index = 0

    def handle_click(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Context:
            self.build_menu()
            self.contextMenu().popup(QtGui.QCursor.pos())

    def build_menu(self):
        self.menu.clear()

        # CPU section
        cpu = psutil.cpu_percent()
        cpu_times = psutil.cpu_times_percent()
        self.menu.addSection(f" CPU: {cpu:.1f}%")
        self.menu.addAction(f"   ├─ User: {cpu_times.user:.1f}%")
        self.menu.addAction(f"   ├─ Kernel: {cpu_times.system:.1f}%")
        self.menu.addAction(f"   └─ Available: {100 - cpu:.1f}%")

        # Memory
        mem = psutil.virtual_memory()
        self.menu.addSection(f" Memory: {mem.percent:.1f}%")
        self.menu.addAction(f"   ├─ Total: {mem.total / (1024**3):.2f} GB")
        self.menu.addAction(f"   ├─ Used: {mem.used / (1024**3):.2f} GB")
        self.menu.addAction(f"   └─ Available: {mem.available / (1024**3):.2f} GB")

        # Storage
        self.menu.addSection(" Storage:")
        for part in psutil.disk_partitions():
            if 'cdrom' in part.opts or not os.path.exists(part.mountpoint):
                continue
            usage = psutil.disk_usage(part.mountpoint)
            self.menu.addAction(f"   ├─ {part.device} {usage.percent}%")
            self.menu.addAction(f"   │  ├─ Used: {usage.used / (1024**3):.2f} GB")
            self.menu.addAction(f"   │  └─ Free: {usage.free / (1024**3):.2f} GB")

        # GPU
        if self.nvml_available:
            self.menu.addSection("🎮 GPU:")
            for i in range(pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle).decode()
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                self.menu.addAction(f"   ├─ {name} ({util.gpu}%)")
                self.menu.addAction(f"   │  ├─ Mem: {mem.used / (1024**3):.2f} / {mem.total / (1024**3):.2f} GB")
                self.menu.addAction(f"   │  └─ Temp: {temp}°C")

        # Runner switch
        runner_menu = self.menu.addMenu("🐾 Runner")
        runner_menu.addAction("🐱 Cat").triggered.connect(lambda: self.set_metric('cpu'))
        runner_menu.addAction("🐴 Horse").triggered.connect(lambda: self.set_metric('gpu'))

        # Theme switch
        theme_menu = self.menu.addMenu("🎨 Theme")
        theme_menu.addAction("Dark").triggered.connect(lambda: self.set_theme('dark'))
        theme_menu.addAction("Light").triggered.connect(lambda: self.set_theme('light'))

        self.menu.addSeparator()
        self.menu.addAction("❌ Exit", QtWidgets.qApp.quit)

    def set_metric(self, metric):
        if self.metric != metric:
            self.metric = metric
            self.reload_icons()

    def set_theme(self, theme):
        if self.theme != theme:
            self.theme = theme
            self.reload_icons()

    def update_metrics(self):
        value = self.get_cpu_usage() if self.metric == 'cpu' else self.get_gpu_usage()
        name = "CPU" if self.metric == 'cpu' else "GPU"
        self.setToolTip(f"{name} Usage: {value:.1f}%")

        if value < 30:
            self.anim_timer.setInterval(800)
        elif value < 70:
            self.anim_timer.setInterval(300)
        else:
            self.anim_timer.setInterval(100)

    def animate_icon(self):
        if self.icons:
            self.setIcon(self.icons[self.frame_index])
            self.frame_index = (self.frame_index + 1) % len(self.icons)

    def get_cpu_usage(self):
        return psutil.cpu_percent()

    def get_gpu_usage(self):
        if not self.nvml_available:
            return 0
        try:
            for i in range(pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                return util.gpu
        except:
            return 0

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray = TrayAnimator()
    sys.exit(app.exec_())
