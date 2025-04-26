import pyvisa
import time

class B2900Controller:
    def __init__(self, address: str, timeout: int = 10000):
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(address)
        self.instrument.timeout = timeout
        self.instrument.write_termination = '\n'
        self.instrument.read_termination = '\n'

    def close(self):
        self.instrument.close()

    def reset(self):
        self.instrument.write("*RST")

    def beep(self, freq=200, duration=1):
        self.instrument.write(f":SYST:BEEP {freq},{duration}")

    def set_beeper(self, state: bool):
        cmd = "ON" if state else "OFF"
        self.instrument.write(f":SYST:BEEP:STAT {cmd}")

    def self_test(self) -> bool:
        result = int(self.instrument.query("*TST?"))
        return result == 0

    def self_calibration(self) -> bool:
        result = int(self.instrument.query("*CAL?"))
        return result == 0

    def get_id(self) -> str:
        return self.instrument.query("*IDN?")

    def read_error(self) -> str:
        return self.instrument.query(":SYST:ERR?")

    def clear_errors(self) -> str:
        return self.instrument.query(":SYST:ERR:ALL?")

    def set_output(self, state: bool):
        cmd = "ON" if state else "OFF"
        self.instrument.write(f":OUTP {cmd}")

    def set_source_mode(self, mode: str):
        assert mode.upper() in ["CURR", "VOLT"]
        self.instrument.write(f":SOUR:FUNC:MODE {mode.upper()}")

    def apply_voltage(self, voltage: float):
        self.set_source_mode("VOLT")
        self.instrument.write(f":SOUR:VOLT {voltage}")

    def apply_current(self, current: float):
        self.set_source_mode("CURR")
        self.instrument.write(f":SOUR:CURR {current}")

    def set_voltage_compliance(self, limit: float):
        self.instrument.write(f":SENS:VOLT:PROT {limit}")

    def set_current_compliance(self, limit: float):
        self.instrument.write(f":SENS:CURR:PROT {limit}")

    def measure_voltage(self) -> float:
        return float(self.instrument.query(":MEAS:VOLT?").strip())

    def measure_current(self) -> float:
        return float(self.instrument.query(":MEAS:CURR?").strip())

    def configure_output_range(self, mode: str, value: float):
        assert mode.upper() in ["VOLT", "CURR"]
        self.instrument.write(f":SOUR:{mode.upper()}:RANG {value}")

    def enable_4wire(self, enable: bool):
        cmd = "ON" if enable else "OFF"
        self.instrument.write(f":SENS:REM {cmd}")

    def set_output_off_mode(self, mode: str):
        assert mode.upper() in ["ZERO", "HIZ", "NORM"]
        self.instrument.write(f":OUTP:OFF:MODE {mode.upper()}")

    def save_status(self, filename: str):
        self.instrument.write(f":MMEM:STOR:STAT \"{filename}\"")
        self.instrument.query("*OPC?")

    def load_status(self, filename: str):
        self.instrument.write(f":MMEM:LOAD:STAT \"{filename}\"")

    def init_output(self):
        self.instrument.write(":INIT")
