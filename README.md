# RAM Visual Overlay - Compact System Monitor V1.0

A clean, customizable, frameless desktop overlay for real-time hardware performance and network latency monitoring across any running application.

## Features

* **Comprehensive Hardware Tracking**: Real-time monitoring of CPU/GPU load, temperature, and power consumption (Watts), plus RAM usage.
* **Smart Alerts**: Metrics dynamically change color (to yellow/red) to warn you instantly when temperatures or RAM usage reach critical thresholds.
* **Advanced Network Monitoring**: Real-time Ping (to 8.8.8.8) and download speed, with a seamless context menu toggle to switch between **MB/s** and **Mbps**.
* **Smart Process Tracking**: Automatically monitors the target application and redirects back to the main menu if the app unexpectedly closes.
* **Premium Overlay UI**: A custom right-click context menu directly on the overlay featuring a smooth transparency slider, global hotkey binding, and window pinning.
* **Perfect Positioning**: Features screen edge snapping (magnet effect) for pixel-perfect placement on your monitor.
* **Persistent State**: Automatically saves exact window X/Y coordinates, pinning state, transparency, and network preferences to `config.json` across restarts.
* **Zero-Lag Architecture**: Asynchronous background threads for hardware polling and network diagnostics ensure your workflow or gaming is never interrupted.

## How to Install & Run

1. Clone the repository:
   ```bash
   git clone https://github.com/Daniil-02/RAM-Visual.git
   cd RAM-Visual
   ```

2. Install the required dependencies:
   ```bash
   pip install PyQt6 psutil
   ```

3. Run the application:
   ```bash
   python main.py
   ```

   > ⚠️ **Note:** It is highly recommended to run your terminal or the application **as Administrator**. This ensures the overlay has proper permissions to accurately read hardware temperatures and detect active system processes without restrictions.
