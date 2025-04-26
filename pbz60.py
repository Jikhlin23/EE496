import pyvisa
import serial

class PBZController:
    def __init__(self, connection_type="USB", resource=None, baudrate=9600, timeout=1):
        """
        Initializes the connection to the PBZ power supply.
        """
        self.connection_type = connection_type.upper()
        self.resource = resource
        self.instrument = None

        try:
            if self.connection_type in ["USB", "GPIB"]:
                rm = pyvisa.ResourceManager()
                print(f"Trying to connect to {self.resource}...")
                self.instrument = rm.open_resource(self.resource)
                print("Connection successful!")
                
            elif self.connection_type == "RS232C":
                self.instrument = serial.Serial(self.resource, baudrate=baudrate, timeout=timeout)
                print("Serial connection successful!")
            else:
                raise ValueError("Unsupported connection type. Use USB, GPIB, or RS232C.")
        except Exception as e:
            print(f"Connection Error: {e}")

    def send_command(self, command):
        """Sends a SCPI command to the instrument."""
        if self.connection_type in ["USB", "GPIB"]:
            return self.instrument.write(command)
        elif self.connection_type == "RS232C":
            self.instrument.write(f"{command}\n".encode())

    def query(self, command):
        """Sends a SCPI query and returns the response."""
        if self.connection_type in ["USB", "GPIB"]:
            return self.instrument.query(command)
        elif self.connection_type == "RS232C":
            self.instrument.write(f"{command}\n".encode())
            return self.instrument.readline().decode().strip()

    def close(self):
        """Closes the connection to the instrument."""
        if self.instrument:
            self.instrument.close()

    # --- SCPI Commands ---
    def identify(self):
        """Returns the device identification string."""
        return self.query("*IDN?")

    def reset(self):
        """Resets the device to its default state."""
        self.send_command("*RST")
        
    def event_status_register(self):
        """ Queries the event status register. """
        return self.query("*ESR?")
    
    def set_voltage(self, voltage):
        """Sets the output voltage."""
        self.send_command(f"VOLT {voltage}")

    def set_current(self, current):
        """Sets the output current."""
        self.send_command(f"CURR {current}")

    def enable_output(self):
        """Enables the output."""
        self.send_command("OUTP ON")

    def disable_output(self):
        """Disables the output."""
        self.send_command("OUTP OFF")

    def measure_voltage(self):
        """Measures and returns the output voltage."""
        return float(self.query("MEAS:VOLT?"))

    def measure_current(self):
        """Measures and returns the output current."""
        return float(self.query("MEAS:CURR?"))

    def set_mode(self, mode="CV"):
        """
        Sets the device mode (CV or CC).
        
        :param mode: CV (Constant Voltage) or CC (Constant Current)
        """
        if mode not in ["CV", "CC"]:
            raise ValueError("Mode must be 'CV' or 'CC'.")
        self.send_command(f"FUNC:MODE {mode}")

    def set_polarity(self, polarity="BIPolar"):
        """
        Sets the output polarity mode.
        
        :param polarity: BIPolar or UNIPolar
        """
        if polarity not in ["BIPolar", "UNIPolar"]:
            raise ValueError("Polarity must be 'BIPolar' or 'UNIPolar'.")
        self.send_command(f"FUNC:POL {polarity}")

    def set_source(self, source = "INT"):
        if source not in ["INT" , "EXT" , "BOTH"]:
            raise ValueError("Sorece must be in [ INT , EXT , BOTH]")
        else:
            self.send_command(f"FUNC:SOUR {source}")

    def set_overvoltage_protection(self, voltage):
        """Sets the overvoltage protection level."""
        self.send_command(f"CURR:PROT:OVER {voltage}")

    # -- Output sub-system --
    
    def output_on(self):
        """Turns the output ON."""
        self.send_command("OUTP ON")

    def output_off(self):
        """Turns the output OFF."""
        self.send_command("OUTP OFF")

    def output_trigger_on(self):
        """Sets output trigger ON."""
        self.send_command("OUTP:TRIG ON")

    def output_trigger_off(self):
        """Sets output trigger OFF."""
        self.send_command("OUTP:TRIG OFF")

    def set_power_on_state(self, state="RST"):
        """Sets output state at power on (RST or AUTO)."""
        if state not in ["RST", "AUTO"]:
            raise ValueError("Invalid state! Use 'RST' or 'AUTO'.")
        self.send_command(f"OUTP:PON:STAT {state}")

    def set_external_control_polarity(self, polarity="NORM"):
        """Sets external control signal polarity (NORM or INV)."""
        if polarity not in ["NORM", "INV"]:
            raise ValueError("Invalid polarity! Use 'NORM' or 'INV'.")
        self.send_command(f"OUTP:EXT {polarity}")

    def set_trigger_polarity(self, polarity="POS"):
        """Sets trigger signal output polarity (POS or NEG)."""
        if polarity not in ["POS", "NEG"]:
            raise ValueError("Invalid polarity! Use 'POS' or 'NEG'.")
        self.send_command(f"OUTP:TRIG:POL {polarity}")

    def trigger_signal_output_on(self):
        """Turns trigger signal output ON."""
        self.send_command("OUTP:TRIG:STAT ON")

    def trigger_signal_output_off(self):
        """Turns trigger signal output OFF."""
        self.send_command("OUTP:TRIG:STAT OFF")

    def option_output_on(self):
        """Turns option output ON."""
        self.send_command("OUTP:PORT ON")

    def option_output_off(self):
        """Turns option output OFF."""
        self.send_command("OUTP:PORT OFF")

    def clear_protection(self):
        """Clears any protection alarms."""
        self.send_command("OUTP:PROT:CLE")

    # -- Input sub-system --

    def trigger_input_polarity(self, polarity = "POS") :
        if polarity not in ["POS" , "NEG"] :
            raise ValueError("Invalid polarity! Use 'POS' or 'NEG'.")
        else: 
            self.send_command(f"INP:TRIG:POL {polarity}")

    # -- SENSe sub-system --

    def set_measurment_time(self, time = 0.1):
        if not (0.0001 <= time <=3600):
            raise ValueError("Invalid input. Time should belong to the range (0.0001 , 3600)")
        else:
            self.send_command(f"SENS:APER: {time}")

    def set_measurement_function(self,function = "DC"):
        if function not in ["DC" , "AC" , "DCAC" , "PEAK"] :
            raise ValueError("Invalid input. Input should belong to ['DC' , 'AC' , 'DCAC' , 'PEAK']")
        else:
            self.send_command(f"SENS:FUNC: {function.upper()}")

    def set_trigger_delay(self, delay = 0):
        """
        Sets the trigger delay (TRIG:DEL) in seconds.
        """
        if not (0 <= delay <= 3600):
            raise ValueError("Delay must be between 0 and 3600 seconds.")
        command = f"SENS:TRIG:DEL {delay}"
        self.send_command(command)

    def set_trigger_source(self, source = "AUTO"):
        """
        Sets the measurement start trigger source (TRIG:SOUR).
        Options: AUTO, INT, EXTPOS, EXTNEG.
        """
        valid_sources = ["AUTO", "INT", "EXTPOS", "EXTNEG"]
        if source.upper() not in valid_sources:
            raise ValueError(f"Source must be one of {', '.join(valid_sources)}.")
        command = f"SENS:TRIG:SOUR {source.upper()}"
        self.send_command(command)

    