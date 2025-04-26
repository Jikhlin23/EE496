

from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument import Instrument

class SR830Wrapper:
    def __init__(self, name='lockin', address='GPIB0::8::INSTR'):
        # Prevent conflicts with previously existing instruments
        if name in Instrument._all_instruments:
            del Instrument._all_instruments[name]
        self.instrument = SR830(name, address)

    # Signal generation and config setters
    def set_sine_out_amplitude(self, voltage: float):
        self.instrument.amplitude.set(voltage)

    def set_frequency(self, freq: float):
        self.instrument.frequency.set(freq)

    def set_phase(self, value: float):
        self.instrument.phase.set(value)

    def set_sensitivity(self, value: str):
        self.instrument.sensitivity.set(value)

    def set_time_constant(self, value: str):
        self.instrument.time_constant.set(value)

    def set_reference_source(self, value: str):
        self.instrument.reference_source.set(value)

    def set_harmonic(self, value: int):
        self.instrument.harmonic.set(value)

    def set_input_config(self, value: str):
        self.instrument.input_config.set(value)

    def set_input_coupling(self, value: str):
        self.instrument.input_coupling.set(value)

    def set_ext_trigger(self, value: bool):
        self.instrument.ext_trigger.set(value)

    # Snap function to read multiple parameters in one call
    def snap_measurements(self, *args):
        return self.instrument.snap(*args)

    # Auto adjustment functions
    def auto_phase(self):
        self.instrument.auto_phase()

    def auto_gain(self):
        self.instrument.auto_gain()

    def auto_reserve(self):
        self.instrument.auto_reserve()

    # Aggregate reading
    def get_all(self):
        return {
            'X': self.instrument.X.get(),
            'Y': self.instrument.Y.get(),
            'R': self.instrument.R.get(),
            'Phase': self.instrument.P.get(),
            'Amplitude': self.instrument.amplitude.get(),
            'Frequency': self.instrument.frequency.get(),
            'Sensitivity': self.instrument.sensitivity.get(),
            'Time Constant': self.instrument.time_constant.get(),
            'Input Config': self.instrument.input_config.get(),
            'Input Coupling': self.instrument.input_coupling.get(),
            'Reference Source': self.instrument.reference_source.get(),
            'Harmonic': self.instrument.harmonic.get(),
            'External Trigger': self.instrument.ext_trigger.get(),
            'Complex Voltage': self.instrument.complex_voltage()
        }

    def close(self):
        self.instrument.close()


