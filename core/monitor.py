import psutil
import time
import ctypes
from PyQt6.QtCore import QThread, pyqtSignal
import win32pdh
import pynvml
import subprocess
import os
import threading
import re

# Структура разделяемой памяти утилиты CoreTemp для чтения показаний без сторонних библиотек
class CoreTempSharedDataEx(ctypes.Structure):
    _fields_ = [
        ("uiLoad", ctypes.c_uint * 256),
        ("uiTjMax", ctypes.c_uint * 128),
        ("uiCoreCnt", ctypes.c_uint),
        ("uiCPUCnt", ctypes.c_uint),
        ("fTemp", ctypes.c_float * 256),
        ("fVID", ctypes.c_float),
        ("fCPUSpeed", ctypes.c_float),
        ("fFSBSpeed", ctypes.c_float),
        ("fMultiplier", ctypes.c_float),
        ("sCPUName", ctypes.c_char * 100),
        ("ucFahrenheit", ctypes.c_ubyte),
        ("ucDeltaToTjMax", ctypes.c_ubyte),
        ("ucTdpSupported", ctypes.c_ubyte),
        ("ucPowerSupported", ctypes.c_ubyte),
        ("uiStructVersion", ctypes.c_uint),
        ("uiTdp", ctypes.c_uint * 128),
        ("fPower", ctypes.c_float * 128),
        ("fMultipliers", ctypes.c_float * 256),
    ]

class SystemMonitor(QThread):
    metrics_updated = pyqtSignal(dict)
    
    def __init__(self, pid):
        super().__init__()
        self.pid = pid
        self.running = True
        self.paused = False
        self.target_name = None
        self.target_exe = None
        
        try:
            target_proc = psutil.Process(pid)
            self.target_name = target_proc.name()
            self.target_exe = target_proc.exe()
        except psutil.NoSuchProcess:
            self.running = False
            return
            
        self.cpu_count = psutil.cpu_count(logical=True)
        self.processes = {} # {pid: psutil.Process()}
        self._update_process_list()
        
        # Настройка PDH для получения загрузки GPU (Windows Performance Counters)
        self.hq = None
        self.gpu_counters = []
        self._setup_gpu_counters()
        
        # Настройка NVML (NVIDIA) в качестве запасного варианта
        self.nvml_inited = False
        try:
            pynvml.nvmlInit()
            self.nvml_inited = True
        except Exception as e:
            pass

        self.ping_enabled = True
        self.last_net_bytes = psutil.net_io_counters().bytes_recv
        self.last_net_time = time.time()
        self.current_download_speed = 0.0

        self.current_ping = "---"
        self.ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.ping_thread.start()

    def set_ping_enabled(self, enabled):
        self.ping_enabled = enabled
        if enabled:
            # Сбрасываем счетчики при включении, чтобы не было скачка скорости
            self.last_net_bytes = psutil.net_io_counters().bytes_recv
            self.last_net_time = time.time()

    def _ping_loop(self):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        while self.running:
            if self.paused or not self.ping_enabled:
                time.sleep(1)
                continue
                
            try:
                result = subprocess.run(
                    ["ping", "-n", "1", "-w", "1000", "8.8.8.8"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    startupinfo=startupinfo,
                    text=True,
                    encoding='cp866',
                    errors='ignore',
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0:
                    output = result.stdout.lower()
                    if "ttl=" in output:
                        match = re.search(r'(?:время|time)[=<]\s*(\d+)\s*(?:мс|ms)', output, re.IGNORECASE)
                        if match:
                            self.current_ping = f"{match.group(1)} ms"
                        else:
                            self.current_ping = "<1 ms" if "<1" in output else "---"
                    else:
                        self.current_ping = "Err"
                else:
                    self.current_ping = "Err"
            except Exception:
                self.current_ping = "Err"
                
            time.sleep(1)

    def _update_process_list(self):
        current_pids = set()
        changed = False
        for p in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                # Группируем все дочерние процессы (например вкладки Chrome) по имени или пути
                if p.info['name'] == self.target_name or p.info['exe'] == self.target_exe:
                    pid = p.info['pid']
                    current_pids.add(pid)
                    if pid not in self.processes:
                        p.cpu_percent(interval=None) # Инициализируем счетчик CPU
                        self.processes[pid] = p
                        changed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        # Удаление завершенных процессов из отслеживания
        dead_pids = set(self.processes.keys()) - current_pids
        for pid in dead_pids:
            del self.processes[pid]
            changed = True
            
        return changed

    def _setup_gpu_counters(self):
        if self.hq:
            try:
                win32pdh.CloseQuery(self.hq)
            except: pass
            self.hq = None
            self.gpu_counters = []
            
        if not self.processes:
            return
            
        try:
            self.hq = win32pdh.OpenQuery()
            items, instances = win32pdh.EnumObjectItems(None, None, "GPU Engine", win32pdh.PERF_DETAIL_WIZARD)
            
            pids = [str(pid) for pid in self.processes.keys()]
            matching_instances = [inst for inst in instances if any(inst.startswith(f"pid_{pid}_") for pid in pids)]
            
            for inst in matching_instances:
                if "engtype_3D" in inst or "engtype_VideoDecode" in inst or "engtype_VideoEncode" in inst:
                    c_path = win32pdh.MakeCounterPath((None, "GPU Engine", inst, None, 0, "Utilization Percentage"))
                    handle = win32pdh.AddCounter(self.hq, c_path)
                    self.gpu_counters.append(handle)
                    
            if self.gpu_counters:
                win32pdh.CollectQueryData(self.hq)
        except Exception as e:
            if self.hq:
                win32pdh.CloseQuery(self.hq)
                self.hq = None

    def get_gpu_usage_pdh(self):
        if not self.hq or not self.gpu_counters:
            return -1.0
        try:
            win32pdh.CollectQueryData(self.hq)
            total_gpu = 0.0
            for handle in self.gpu_counters:
                try:
                    type, val = win32pdh.GetFormattedCounterValue(handle, win32pdh.PDH_FMT_DOUBLE)
                    total_gpu += val
                except Exception:
                    pass
            return total_gpu
        except Exception:
            return -1.0

    def get_gpu_usage_nvml(self):
        if not self.nvml_inited:
            return -1.0
        try:
            deviceCount = pynvml.nvmlDeviceGetCount()
            if deviceCount > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                return float(util.gpu)
            return -1.0
        except Exception:
            return -1.0

    def run(self):
        computer = None
        try:
            import clr
            import sys
            import os
            # Добавляем корень проекта в пути поиска DLL
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_dir not in sys.path:
                sys.path.append(project_dir)
                
            clr.AddReference("LibreHardwareMonitorLib")
            from LibreHardwareMonitor.Hardware import Computer
            
            computer = Computer()
            computer.IsCpuEnabled = True
            computer.IsGpuEnabled = True
            computer.Open()
        except Exception as e:
            print(f"Ошибка загрузки LibreHardwareMonitorLib: {e}", flush=True)

        def get_cpu_temp():
            if not computer: return None
            try:
                for hw in computer.Hardware:
                    if 'Cpu' in str(hw.HardwareType):
                        hw.Update()
                        temps = []
                        for sensor in hw.Sensors:
                            if str(sensor.SensorType) == 'Temperature':
                                if sensor.Value is not None:
                                    temps.append(float(sensor.Value))
                        if temps:
                            return max(temps)
            except Exception:
                pass
            return None

        def get_gpu_temp():
            # Приоритет NVML, он быстрее
            if self.nvml_inited:
                try:
                    if pynvml.nvmlDeviceGetCount() > 0:
                        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                        return float(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
                except Exception:
                    pass
                    
            if not computer: return None
            try:
                for hw in computer.Hardware:
                    if 'Gpu' in str(hw.HardwareType):
                        hw.Update()
                        for sensor in hw.Sensors:
                            if str(sensor.SensorType) == 'Temperature':
                                if sensor.Value is not None:
                                    return float(sensor.Value)
            except Exception:
                pass
            return None

        def get_cpu_power():
            """Чтение мощности CPU пакета через LibreHardwareMonitor (Вт)."""
            if not computer: return None
            try:
                for hw in computer.Hardware:
                    if 'Cpu' in str(hw.HardwareType):
                        hw.Update()
                        for sensor in hw.Sensors:
                            # Ищем Package Power — суммарная мощность всего CPU
                            if str(sensor.SensorType) == 'Power':
                                name = str(sensor.Name).lower()
                                if 'package' in name or 'cpu' in name:
                                    if sensor.Value is not None:
                                        return float(sensor.Value)
            except Exception:
                pass
            return None

        def get_gpu_power():
            """Чтение мощности GPU через NVML (NVIDIA). Для AMD — через LibreHardwareMonitor."""
            # Приоритет: NVML для NVIDIA
            if self.nvml_inited:
                try:
                    if pynvml.nvmlDeviceGetCount() > 0:
                        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                        mw = pynvml.nvmlDeviceGetPowerUsage(handle)  # milliwatts
                        return mw / 1000.0
                except Exception:
                    pass
            # Fallback: LibreHardwareMonitor для AMD и других
            if not computer: return None
            try:
                for hw in computer.Hardware:
                    if 'Gpu' in str(hw.HardwareType):
                        hw.Update()
                        for sensor in hw.Sensors:
                            if str(sensor.SensorType) == 'Power':
                                if sensor.Value is not None:
                                    return float(sensor.Value)
            except Exception:
                pass
            return None

        loop_count = 0
        try:
            while self.running and self.processes:
                # ГЛАВНАЯ ОПТИМИЗАЦИЯ: полный простой (0% CPU), пока оверлей скрыт
                if self.paused:
                    time.sleep(0.5)
                    continue
                    
                try:
                    # Обновляем список процессов каждые 3 секунды, чтобы ловить новые окна/вкладки приложения
                    if loop_count % 3 == 0:
                        if self._update_process_list():
                            self._setup_gpu_counters()
                    loop_count += 1
                    
                    total_cpu = 0.0
                    total_ram_mb = 0.0
                    
                    # Суммируем метрики по всем найденным экземплярам процесса
                    for pid, proc in list(self.processes.items()):
                        try:
                            total_cpu += proc.cpu_percent(interval=None)
                            
                            # psutil.memory_info().private в Windows возвращает Private Bytes (Commit Size),
                            # что вызывает огромные значения для Java (6000 MB).
                            # Истинный "Private Working Set" (как в Task Manager) — это USS (Unique Set Size).
                            try:
                                ram = proc.memory_full_info().uss
                            except (psutil.AccessDenied, AttributeError):
                                ram = proc.memory_info().rss
                                
                            total_ram_mb += ram / (1024 * 1024)
                        except psutil.NoSuchProcess:
                            del self.processes[pid]
                            
                    # Нормализуем значение CPU по количеству логических ядер (как в Task Manager)
                    if self.cpu_count and self.cpu_count > 0:
                        total_cpu = total_cpu / self.cpu_count
                    
                    gpu = self.get_gpu_usage_pdh()
                    if gpu < 0:
                        gpu = self.get_gpu_usage_nvml()
                    
                    cpu_temp = get_cpu_temp()
                    gpu_temp = get_gpu_temp()
                    cpu_power = get_cpu_power()
                    gpu_power = get_gpu_power()
                    
                    if self.ping_enabled:
                        net_io = psutil.net_io_counters()
                        current_time = time.time()
                        dt = current_time - self.last_net_time
                        if dt > 0:
                            bytes_diff = net_io.bytes_recv - self.last_net_bytes
                            self.current_download_speed = (bytes_diff / dt) / (1024 * 1024)
                        self.last_net_bytes = net_io.bytes_recv
                        self.last_net_time = current_time
                    else:
                        self.current_download_speed = 0.0
                    
                    self.metrics_updated.emit({
                        'cpu': total_cpu,
                        'ram': total_ram_mb,
                        'gpu': gpu,
                        'cpu_temp': cpu_temp,
                        'gpu_temp': gpu_temp,
                        'cpu_power': cpu_power,
                        'gpu_power': gpu_power,
                        'ping': self.current_ping,
                        'download_speed': self.current_download_speed
                    })
                    
                    self.msleep(1000) # Обновление раз в секунду (Qt-нативный безопасный сон)
                    
                except Exception as e:
                    print(f"Ошибка в цикле мониторинга: {e}", flush=True)
                    self.msleep(1000)
        finally:
            # Гарантированное закрытие аппаратной сессии при выходе из потока
            if computer:
                try:
                    computer.Close()
                except Exception:
                    pass
                    
    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False
        if self.hq:
            try:
                win32pdh.CloseQuery(self.hq)
            except: pass
        if self.nvml_inited:
            try:
                pynvml.nvmlShutdown()
            except: pass
        self.wait()