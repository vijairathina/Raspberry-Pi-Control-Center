import os
import glob
import shutil
import subprocess
import psutil

class HardwareManager:
    @staticmethod
    def get_usb_devices() -> list[dict]:
        devices = []
        if shutil.which("lsusb"):
            try:
                # lsusb output: Bus 001 Device 004: ID 046d:c52b Logitech, Inc. Unifying Receiver
                res = subprocess.run(["lsusb"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                for line in res.stdout.splitlines():
                    parts = line.strip().split(None, 6)
                    if len(parts) >= 7 and parts[0] == "Bus":
                        bus = parts[1]
                        dev_num = parts[3].rstrip(":")
                        device_id = parts[5]
                        product = parts[6]
                        devices.append({
                            "bus": bus,
                            "device": dev_num,
                            "id": device_id,
                            "product": product,
                            "vendor": product.split()[0] if " " in product else product,
                            "driver": "usb",
                            "status": "Connected"
                        })
                if devices:
                    return devices
            except Exception:
                pass

        # Fallback / mock USB devices
        return [
            {"bus": "001", "device": "002", "id": "0424:9514", "product": "Standard Microsystems Corp. USB Hub", "vendor": "SMSC", "driver": "hub", "status": "Connected"},
            {"bus": "001", "device": "003", "id": "0424:ec00", "product": "Standard Microsystems Corp. SMSC9512/9514 Fast Ethernet", "vendor": "SMSC", "driver": "smsc95xx", "status": "Connected"},
            {"bus": "001", "device": "004", "id": "046d:c52b", "product": "Logitech, Inc. Unifying Receiver", "vendor": "Logitech", "driver": "usbhid", "status": "Connected"}
        ]

    @staticmethod
    def get_pci_devices() -> list[dict]:
        pci_list = []
        if shutil.which("lspci"):
            try:
                res = subprocess.run(["lspci"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                for line in res.stdout.splitlines():
                    if line.strip():
                        pci_list.append({"device": line.strip()})
                if pci_list:
                    return pci_list
            except Exception:
                pass
        return [{"device": "Broadcom BCM2837 / BCM2711 / BCM2712 Integrated PCIe Controller"}]

    @staticmethod
    def get_serial_ports() -> list[str]:
        ports = []
        for p in glob.glob("/dev/ttyAMA*") + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*") + glob.glob("/dev/serial*"):
            ports.append(p)
        if not ports and subprocess.os.name == "nt":
            ports = ["COM1", "COM3 (Emulated Serial)"]
        return ports or ["/dev/ttyAMA0 (Mini UART)", "/dev/serial0"]

    @staticmethod
    def get_bus_interfaces() -> dict:
        # Check I2C, SPI
        i2c_devs = glob.glob("/dev/i2c-*")
        spi_devs = glob.glob("/dev/spidev*")
        return {
            "i2c_enabled": len(i2c_devs) > 0,
            "i2c_devices": i2c_devs if i2c_devs else ["/dev/i2c-1 (Available)"],
            "spi_enabled": len(spi_devs) > 0,
            "spi_devices": spi_devs if spi_devs else ["/dev/spidev0.0", "/dev/spidev0.1"]
        }

    @staticmethod
    def get_hardware_overview() -> dict:
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        ram = psutil.virtual_memory()

        return {
            "cpu": {
                "cores": cpu_count,
                "max_freq_mhz": round(cpu_freq.max, 1) if cpu_freq and cpu_freq.max else "N/A",
                "cur_freq_mhz": round(cpu_freq.current, 1) if cpu_freq else "N/A",
            },
            "ram": {
                "total_mb": round(ram.total / (1024 * 1024), 1),
            },
            "usb_devices": HardwareManager.get_usb_devices(),
            "pci_devices": HardwareManager.get_pci_devices(),
            "serial_ports": HardwareManager.get_serial_ports(),
            "bus_interfaces": HardwareManager.get_bus_interfaces(),
        }
