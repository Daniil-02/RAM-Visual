# RAM Visual Overlay - Compact System Monitor

A clean, customizable, frameless desktop overlay for real-time hardware performance and network latency monitoring across any running application.

## Features

* Real-time tracking of RAM usage, CPU load & temperature, and GPU load & temperature.
* Dynamic real-time Network Ping (to `8.8.8.8`) and download speed (in MB/s) monitoring.
* Zero-lag asynchronous background threads for hardware polling and network diagnostics ensuring your workflow is never interrupted.
* Sleek system tray context menu with a toggle to dynamically show/hide the Network metrics row.
* Smart adaptive window resizing with smooth animations (no empty gaps when metrics are hidden, seamlessly shrinking or expanding the layout).

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
