# RAM Visual Overlay

A clean, customizable, frameless gaming overlay for monitoring system stats and network latency in real-time.

## Features

* Real-time RAM usage, CPU load & temperature, and GPU load & temperature tracking.
* Dynamic real-time Network Ping (to `8.8.8.8`) and download speed (in MB/s) monitoring.
* Zero-lag asynchronous background threads for hardware polling and network diagnostics.
* Sleek system tray context menu with a toggle to dynamically show/hide the PING row.
* Smart adaptive window resizing with smooth animations (no empty gaps when metrics are hidden).

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
