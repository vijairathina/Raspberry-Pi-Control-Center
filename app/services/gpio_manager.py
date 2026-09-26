import os

# Standard 40-Pin Raspberry Pi Header Definition
# Marks safe user GPIOs vs hardware power/ground/system pins
DEFAULT_PINS = [
    {"pin": 1, "gpio": None, "name": "3V3 Power", "type": "power", "mode": "VCC", "state": 1, "safe": False},
    {"pin": 2, "gpio": None, "name": "5V Power", "type": "power", "mode": "VCC", "state": 1, "safe": False},
    {"pin": 3, "gpio": 2, "name": "GPIO 2 (SDA1)", "type": "i2c", "mode": "IN", "state": 1, "safe": True},
    {"pin": 4, "gpio": None, "name": "5V Power", "type": "power", "mode": "VCC", "state": 1, "safe": False},
    {"pin": 5, "gpio": 3, "name": "GPIO 3 (SCL1)", "type": "i2c", "mode": "IN", "state": 1, "safe": True},
    {"pin": 6, "gpio": None, "name": "Ground", "type": "ground", "mode": "GND", "state": 0, "safe": False},
    {"pin": 7, "gpio": 4, "name": "GPIO 4 (GPCLK0)", "type": "gpio", "mode": "OUT", "state": 0, "safe": True},
    {"pin": 8, "gpio": 14, "name": "GPIO 14 (TXD0)", "type": "uart", "mode": "OUT", "state": 1, "safe": True},
    {"pin": 9, "gpio": None, "name": "Ground", "type": "ground", "mode": "GND", "state": 0, "safe": False},
    {"pin": 10, "gpio": 15, "name": "GPIO 15 (RXD0)", "type": "uart", "mode": "IN", "state": 1, "safe": True},
    {"pin": 11, "gpio": 17, "name": "GPIO 17", "type": "gpio", "mode": "OUT", "state": 0, "safe": True},
    {"pin": 12, "gpio": 18, "name": "GPIO 18 (PCM_CLK)", "type": "gpio", "mode": "IN", "state": 0, "safe": True},
    {"pin": 13, "gpio": 27, "name": "GPIO 27", "type": "gpio", "mode": "OUT", "state": 0, "safe": True},
    {"pin": 14, "gpio": None, "name": "Ground", "type": "ground", "mode": "GND", "state": 0, "safe": False},
    {"pin": 15, "gpio": 22, "name": "GPIO 22", "type": "gpio", "mode": "IN", "state": 0, "safe": True},
    {"pin": 16, "gpio": 23, "name": "GPIO 23", "type": "gpio", "mode": "OUT", "state": 0, "safe": True},
    {"pin": 17, "gpio": None, "name": "3V3 Power", "type": "power", "mode": "VCC", "state": 1, "safe": False},
    {"pin": 18, "gpio": 24, "name": "GPIO 24", "type": "gpio", "mode": "IN", "state": 0, "safe": True},
    {"pin": 19, "gpio": 10, "name": "GPIO 10 (MOSI)", "type": "spi", "mode": "OUT", "state": 0, "safe": True},
    {"pin": 20, "gpio": None, "name": "Ground", "type": "ground", "mode": "GND", "state": 0, "safe": False},
    {"pin": 21, "gpio": 9, "name": "GPIO 9 (MISO)", "type": "spi", "mode": "IN", "state": 0, "safe": True},
    {"pin": 22, "gpio": 25, "name": "GPIO 25", "type": "gpio", "mode": "OUT", "state": 0, "safe": True},
    {"pin": 23, "gpio": 11, "name": "GPIO 11 (SCLK)", "type": "spi", "mode": "OUT", "state": 0, "safe": True},
    {"pin": 24, "gpio": 8, "name": "GPIO 8 (CE0)", "type": "spi", "mode": "OUT", "state": 1, "safe": True},
    {"pin": 25, "gpio": None, "name": "Ground", "type": "ground", "mode": "GND", "state": 0, "safe": False},
    {"pin": 26, "gpio": 7, "name": "GPIO 7 (CE1)", "type": "spi", "mode": "OUT", "state": 1, "safe": True},
    {"pin": 27, "gpio": 0, "name": "ID_SD (EEPROM)", "type": "eeprom", "mode": "SYS", "state": 1, "safe": False},
    {"pin": 28, "gpio": 1, "name": "ID_SC (EEPROM)", "type": "eeprom", "mode": "SYS", "state": 1, "safe": False},
    {"pin": 29, "gpio": 5, "name": "GPIO 5", "type": "gpio", "mode": "IN", "state": 1, "safe": True},
    {"pin": 30, "gpio": None, "name": "Ground", "type": "ground", "mode": "GND", "state": 0, "safe": False},
    {"pin": 31, "gpio": 6, "name": "GPIO 6", "type": "gpio", "mode": "IN", "state": 1, "safe": True},
    {"pin": 32, "gpio": 12, "name": "GPIO 12 (PWM0)", "type": "gpio", "mode": "OUT", "state": 0, "safe": True},
    {"pin": 33, "gpio": 13, "name": "GPIO 13 (PWM1)", "type": "gpio", "mode": "OUT", "state": 0, "safe": True},
    {"pin": 34, "gpio": None, "name": "Ground", "type": "ground", "mode": "GND", "state": 0, "safe": False},
    {"pin": 35, "gpio": 19, "name": "GPIO 19 (MISO)", "type": "gpio", "mode": "IN", "state": 0, "safe": True},
    {"pin": 36, "gpio": 16, "name": "GPIO 16", "type": "gpio", "mode": "OUT", "state": 0, "safe": True},
    {"pin": 37, "gpio": 26, "name": "GPIO 26", "type": "gpio", "mode": "OUT", "state": 0, "safe": True},
    {"pin": 38, "gpio": 20, "name": "GPIO 20 (MOSI)", "type": "gpio", "mode": "IN", "state": 0, "safe": True},
    {"pin": 39, "gpio": None, "name": "Ground", "type": "ground", "mode": "GND", "state": 0, "safe": False},
    {"pin": 40, "gpio": 21, "name": "GPIO 21 (SCLK)", "type": "gpio", "mode": "IN", "state": 0, "safe": True},
]

# In-memory pin state table
_pins_state = [dict(p) for p in DEFAULT_PINS]

class GPIOManager:
    @staticmethod
    def get_pins() -> list[dict]:
        return _pins_state

    @staticmethod
    def set_pin_mode(gpio_num: int, mode: str) -> tuple[bool, str]:
        if mode not in ("IN", "OUT"):
            return False, "Mode must be 'IN' or 'OUT'"

        for p in _pins_state:
            if p["gpio"] == gpio_num:
                if not p["safe"]:
                    return False, f"GPIO {gpio_num} (Pin {p['pin']}) is a system/power pin and cannot be modified"
                p["mode"] = mode
                return True, f"GPIO {gpio_num} set to mode {mode}"

        return False, f"GPIO {gpio_num} not found"

    @staticmethod
    def set_pin_state(gpio_num: int, state: int) -> tuple[bool, str]:
        if state not in (0, 1):
            return False, "State must be 0 (OFF) or 1 (ON)"

        for p in _pins_state:
            if p["gpio"] == gpio_num:
                if not p["safe"]:
                    return False, f"GPIO {gpio_num} is protected from modification"
                if p["mode"] != "OUT":
                    return False, f"GPIO {gpio_num} is set to IN. Set mode to OUT before changing output value."
                p["state"] = state
                return True, f"GPIO {gpio_num} turned {'ON (HIGH)' if state == 1 else 'OFF (LOW)'}"

        return False, f"GPIO {gpio_num} not found"
