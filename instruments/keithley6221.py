from typing import Tuple, List, Dict, Union, Optional
import pyvisa
import time
import pyvisa.constants
import pyvisa.resources as visa_res
import logging
import enum
import matplotlib.pyplot as plt
from datetime import datetime

logger = logging.getLogger(__name__)


class Keithley6221:
    class WAVE_RANGES(enum.Enum):
        BEST = "BEST"
        FIXED = "FIX"

    class WAVE_FUNC(enum.Enum):
        SIN = "SIN"
        SQUARE = "SQU"
        RAMP = "RAMP"
        ARBITRARY_0 = "ARB0"
        ARBITRARY_1 = "ARB1"
        ARBITRARY_2 = "ARB2"
        ARBITRARY_3 = "ARB3"
        ARBITRARY_4 = "ARB4"

    class CURRENT_RANGES(enum.Enum):
        R1_2nA = 2e-9
        R2_20nA = 20e-9
        R3_200nA = 200e-9
        R4_2uA = 2e-6
        R5_20uA = 20e-6
        R6_200uA = 200e-6
        R7_2mA = 2e-3
        R8_20mA = 20e-3
        R9_100mA = 100e-3

    class ON_OFF_STATE(enum.Enum):
        ON = "ON"
        OFF = "OFF"

    class UNITS(enum.Enum):
        Volts = "V"
        Ohms = "OHMS"
        Watts = "W"
        Siemens = "SIEM"


    MINIMUM_CURRENT = 2e-12

    def __init__(self,
                 rm: pyvisa.ResourceManager,
                 address: str,
                 device_name: str="",
                 baud_rate: int=9600
                 ):
        params = dict()
        if "com" in address.lower():
            params["baud_rate"] = baud_rate
            params["read_termination"] = '\r'
            params["data_bits"] = 8
            params["parity"] = pyvisa.constants.Parity.none
            params["stop_bits"] = pyvisa.constants.StopBits.one
        elif "gpib" in address.lower():
            params["read_termination"] = '\n'
        elif "tcpip0" in address.lower():
            params["read_termination"] = '\n'
        elif "tcpip" in address.lower():
            # address = "TCPIP::10.8.1.2::1394::SOCKET"
            params["read_termination"] = '\n'
        else:
            raise Exception("Unknown and unsupported port type: Not COM-port or GPIB-port")
        self._device: Union[visa_res.GPIBInstrument, visa_res.SerialInstrument] = rm.open_resource(address, **params)
        self._device.timeout = 10000
        self._device_name = device_name
        self._address = address
        self._rm = rm
        logger.info(f"Device Keithley6221 [{self._address}] is initialized successfully!")

    ########################################################################
    #     Sin Wave
    ########################################################################

    def RunSinWave(
            self,
            frequency: float,
            amplitude: float,
            offset: float=0,
            wave_range: Union[float, CURRENT_RANGES, None]=None,
            duration: Optional[float]=None,
    ) -> None:
        logger.info(f"Keithley 6221 : Set SIN wave with A=[{amplitude}],F=[{frequency}],O=[{offset}],Duration=[{duration}]")
        self.restore_defaults()
        self.set_wave_func(func=self.WAVE_FUNC.SIN)
        self.set_wave_frequency(frequency)
        self.set_wave_amplitude(rms=amplitude)
        self._device.write(f"SOUR:WAVE:OFFS {offset}")
        self._device.write(f"SOUR:WAVE:PMAR:STAT OFF")
        self._device.write(f"SOUR:WAVE:PMAR:OLIN 4")
        self.set_wave_duration(duration=duration)
        if wave_range is None:
            self.set_wave_range(range=self.WAVE_RANGES.BEST)
        else:
            self.set_wave_range(range=self.WAVE_RANGES.FIXED)
            self.set_current_range(wave_range)
        self._device.write(f"SOUR:WAVE:EXTR ON")
        self._device.write(f"SOUR:WAVE:EXTR:ILIN 3")
        self._device.write(f"SOUR:WAVE:EXTR:IGN OFF")
        self._device.write(f"SOUR:WAVE:EXTR:IVAL 0.00")
        self._device.write("SOUR:WAVE:ARM")
        self._device.write("SOUR:WAVE:INIT")

    def Abort(self):
        self._device.write("SOUR:WAVE:ABOR")
        # time.sleep(2)
        # self.turn_output_off()

    def ChangeSinWaveAmplitude(
            self,
            value: float
    ) -> None:
        # self._device.write(f"SOUR:WAVE:ABOR")
        logger.info(f"Keithley 6221 : SIN wave set A=[{value * (2 ** 0.5)}]")
        self.set_wave_amplitude(rms=value)
        self._device.write(f"SOUR:WAVE:ARM")
        # self._device.write(f"SOUR:WAVE:INIT")
        actual_range = self.get_current_range()
        actual_amplitude = self.get_wave_amplitude()
        logger.info(f"Actual RANGE = [{actual_range}]")
        logger.info(f"Actual AMPLITUDE = [{actual_amplitude * (2 ** 0.5)}]")
        self.get_error_status()

    def ChangeSinWaveFrequency(
            self,
            value: float,
    ) -> None:
        logger.info(f"Keithley 6221 : SIN wave set F=[{value}]")
        self.set_wave_frequency(frequency=value)
        self._device.write(f"SOUR:WAVE:ARM")
        actual_frequency = self.get_wave_frequency()
        logger.info(f"Actual FREQUENCY = [{actual_frequency}]")
        self.get_error_status()

    def RunDeltaMeasurements(
            self,
            units: UNITS,
            current: float=1e-6,
            delay: float=10e-3,
            count: Union[int,str]="INF",
            swe_count: int=1,
    ) -> None:

        """
        Эта функция запускать процесс измерения данных, но не хранит ничего в буфере.
        Это значит, что данные можно будет получать просто запросом -- get_delta_data или что-то в этом роде
        """
        enable_compliance_abort = self.ON_OFF_STATE.ON
        is_2182_ok = self.get_delta_2182_presence()
        if not is_2182_ok:
            logger.warning("Cannot establish a connection between 6221 and 2182A via nul-modem cable")
            return
        logger.info("Connection to Keithley2182A was established successfully!")
        if self.get_output_state():
            logging.info("Keithley6221 output=ON detected. Turning it OFF.")
            self.turn_output_off()
        logger.info("Restore defaults")
        self.restore_defaults()
        self.get_error_status()
        logger.info("Set units to OHMS")
        #self.set_units(self.UNITS.Ohms)
        self._device.write(f"UNIT:VOLT:DC {units.value}")
        self.get_error_status()
        logger.info("Query units")
        units = self.get_units()
        self.get_error_status()
        logging.info(f"Current units on Keithley6221 = [{units.value}]")
        logger.info(f"Setting high source value = {current}")
        self._device.write(f"SOUR:DELT:HIGH {current}")
        self.get_error_status()
        logger.info(f"Setting low source value={-current}")
        self._device.write(f"SOUR:DELT:LOW {-current}")
        self.get_error_status()
        logger.info(f"Setting delta delay = {delay}")
        self._device.write(f"SOUR:DELT:DELay {delay}")
        self.get_error_status()
        logger.info(f"Settings Count {count}")
        self._device.write(f"SOUR:DELT:COUN {count}")
        self.get_error_status()
        logger.info(f"Setting the number of measurement sets to repeat = [{swe_count}]")
        self._device.write(f"SOUR:SWE:COUN {swe_count}")
        self.get_error_status()
        # logger.info("Enable cold switching mode.")
        # self._device.write(f"SOUR:DELT:CSWitch 0")
        # self.get_error_status()
        self._device.write(f"SOUR:DELT:CAB {enable_compliance_abort.value}")
        self.get_error_status()
        self.get_opc()
        self._device.write("SOUR:DELT:ARM")
        time.sleep(2)
        self.get_opc()
        self.get_error_status()
        self._device.write("INIT:IMM")
        time.sleep(2)
        self.get_error_status()
        # # To disarm -- SOUR:SWE:ABOR

    ########################################################################
    #     Linear Sweep
    ########################################################################
    def RunDifferentialConductanceMeasurements(
            self,
            start_current: float=0,
            stop_current: float=1000e-6,
            step_size: float=1e-6,
            delta: float=20e-6,
            delay: float=1e-1,
            buffer_points: int=60000,
            rate_2182a_in_nplc: int=5,
    ) -> None:
        enable_compliance_abort = self.ON_OFF_STATE.ON
        is_2182_ok = self.get_dcond_2182_presence()
        if not is_2182_ok:
            logger.warning("Cannot establish a connection between 6221 and 2182A via nul-modem cable")
            return
        if self.get_output_state():
            logging.info("Keithley6221 output=ON detected. Turning it OFF.")
            self.turn_output_off()
        self.restore_defaults()
        units = self.get_units()
        logging.info(f"Current units on Keithley6221 = [{units.value}]")

        if True: # First, initialize START CURRENT
            logger.info(f"Setting START_CURRENT value to [{start_current}]")
            assert -105e-3 < start_current < 105e-3
            self._device.write(f"SOUR:DCON:STARt {start_current}")
            print("And START_CURRENT = ", self._device.query("SOUR:DCON:STAR?").strip())
            self.get_error_status()

        if True: # Second, initialize STOP CURRENT
            logger.info(f"Setting STOP_CURRENT value to [{stop_current}]")
            assert -105e-3 < stop_current < 105e-3
            self._device.write(f"SOUR:DCON:STOP {stop_current}")
            print("And STOP_CURRENT = ", self._device.query("SOUR:DCON:STOP?").strip())
            self.get_error_status()

        if True: # Third, initialize STEP. It should not be changed before STOP CURRENT
            logger.info(f"Setting STEP value to [{step_size}]")
            assert 0 < step_size < 105e-3
            self._device.write(f"SOUR:DCON:STEP {step_size}")
            print("And STEP = ", self._device.query("SOUR:DCON:STEP?").strip())
            self.get_error_status()

        if True:
            logger.info(f"Setting DELTA value to [{delta}]")
            assert 0 < delta < 105e-3
            self._device.write(f"SOUR:DCON:DELTa 1e-6")
            print("And DELTA = ", self._device.query("SOUR:DCON:DELTa?").strip())
            self.get_error_status()

        if True:
            assert 1e-3 < delay < 9999.999
            self._device.write(f"SOUR:DCON:DELay {delay}")
            self.get_error_status()

        self._device.write(f"SOUR:DCON:CAB {enable_compliance_abort.value}")
        self.get_error_status()
        self._device.write(f"TRAC:POIN {buffer_points}")
        self.get_error_status()
        self._device.write("SOUR:DCON:ARM")
        self.get_error_status()
        self._device.write("INIT:IMM")
        print("dIdV program is fully initialized!")
        # self.get_error_status()
        # To disarm -- SOUR:SWE:ABOR
        return

    def GetData(self) -> float:
        response = self._device.query("SENS:DATA?")
        #print(response)
        #print(self.get_units())
        return float(response.split(',')[0])

    ########################################################################
    #     Linear Sweep
    ########################################################################
    def RunLinSweep(self, st: float, en: float, step: float):
        self._device.write(f"*RST")
        self._device.write(f"SOUR:SWE:SPAC LIN")
        self._device.write(f"SOUR:CURR:STAR {st}")
        self._device.write(f"SOUR:CURR:STOP {en}")
        self._device.write(f"SOUR:CURR:STEP {step}")
        self._device.write(f"SOUR:DEL 0.01")
        self._device.write(f"SOUR:SWE:RANG BEST")
        self._device.write(f"SOUR:SWE:COUN 1")
        self._device.write(f"SOUR:SWE:CAB OFF")
        self._device.write(f"SOUR:SWE:ARM")
        self._device.write(f"INIT")

    #######################################################
    #   Внизу только атомарные функции
    #######################################################

    def get_output_state(self) -> bool:
        response_output_state = self._device.query("OUTP?")
        try:
            output_state = int(response_output_state)
        except ValueError:
            logger.critical(f"Cannot convert [{response_output_state}] to int")
            raise
        logger.info(f"Output State = {output_state}, {type(output_state)}")
        return output_state > 0

    def turn_output_on(self):
        self._device.write("OUTP ON")

    def turn_output_off(self):
        self._device.write("OUTP OFF")

    def restore_defaults(self):
        self._device.write("*RST")

    def get_idn(self) -> str:
        idn = self._device.query("*IDN?")
        logger.info(f"{self._address} <--> {idn}")
        # self.get_opc()
        return idn

    # def common_wait(self):
    #     old_timeout = self._device.timeout
    #     self._device.timeout = 10 * 1000  # -- 10 seconds
    #     result = self._device.query("*OPC?").strip()
    #     self._device.timeout = old_timeout
    #     logger.info(f"Check OPC? ---> {result}")
    #     return

    def get_opc(self):
        case = 1
        if case == 1:
            old_timeout = self._device.timeout
            self._device.timeout = 10 * 1000 # -- 10 seconds
            result = self._device.query("*OPC?").strip()
            self._device.timeout = old_timeout
            logger.info(f"Check OPC? ---> {result}")
            return
        else:
            for _ in range(5):
                try:
                    result = self._device.query("*OPC?").strip()
                    logger.info(f"Check OPC? ---> {result}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to get OPC -- timeout -- {e}")
            return

    def get_error_status(self) -> str:
        response = self._device.query(f"SYST:ERR?")
        logger.info(f"Error status on Keithley 6221 = [{response}]")
        return response

    def set_current_range(self, range: Union[float, CURRENT_RANGES]) -> None:
        if isinstance(range, float):
            value = range
        elif isinstance(range, self.CURRENT_RANGES):
            value = range.value
        else:
            value = 100e-3
        self._device.write(f"SOUR:CURR:RANG {value}")
        self.get_error_status()

    def set_current_compliance(self, compliance: float=10.0):
        self._device.write(f"SOUR:CURR:COMP {compliance}")
        self.get_error_status()

    def set_current_range_auto(self, state: Union[ON_OFF_STATE, bool]):
        if isinstance(state, self.ON_OFF_STATE):
            value = state.value
        elif isinstance(state, bool):
            if state:
                value = self.ON_OFF_STATE.ON.value
            else:
                value = self.ON_OFF_STATE.OFF.value
        else:
            raise Exception(f"Unsupported type = [{type(state)}]. "
                            f"Only [{type(bool)}, {type(self.ON_OFF_STATE)}] are supported.")
        self._device.write(f"SOUR:CURR:RANG:AUTO {value}")

    def get_current_range_auto(self) -> str:
        """TODO: check type and return some reasonable type like ON_OFF_STATE"""
        return self._device.query(f"SOUR:CURR:RANG:AUTO?")

    def get_current_range(self) -> float:
        response = self._device.query(f"SOUR:CURR:RANG?")
        logger.info(f"Here is the response [{response}]")
        return float(response)

    def set_wave_func(self, func: WAVE_FUNC):
        self._device.write(f"SOUR:WAVE:FUNC {func.value}")

    def get_status_st(self):
        # TODO 321 page
        # response = self._device.query(f"*STB?")
        response = self._device.query(f"CONDition?")
        # response = self._device.query(f"STAT:MEAS:ENAB?")
        # self._device.write("STAT:MEAS:ENAB 512")

        self.get_error_status()
        print(f"HERE IS THE RESPONSE = [{response}]")

    def set_wave_range(self, range: WAVE_RANGES) -> None:
        """
        Selects whether to use the best-fixed range or whether to use a fixed range. If
        best range is selected, the source range will automatically be selected based
        on the source values. For fixed range, the source range will be left on the
        range it was at when the waveform is started. If the present current range is
        too low when the waveform is started, Error -222 Parameter Out of Range is
        generated, and the waveform does not initiate. This command is not accepted
        while the wave is armed (Error +404 Not allowed with Wave Armed).

        Если установлен BEST range, то в зависимости от текущей амплитуды на этапе ARM'а происходит выбор range'а,
        который не будет изменяться до наступления следующего ARM'a.

        """
        self._device.write(f"SOUR:WAVE:RANG {range.value}")

    def set_wave_amplitude(self, rms: float):
        """
        Поскольку мы большую часть времени работаем с локанами, то все наши данные идут как RMS.
        Keithley6221 по умолчанию работает как one-half the peak-to-peak value,
        иными словами, просто амплитуда. Поэтому когда я говорю, что хочу иметь определённую амплитуду, то
        хочу видеть это значение на локине, то есть мне нужно задавать соотвествующий RMS,
        поэтому мне надо умножать на 1.41.
        : amplitude -- RMS
        """
        coefficient_from_effective_current = 2 ** 0.5
        peak = rms * coefficient_from_effective_current
        value_to_write = max(peak, self.MINIMUM_CURRENT)
        self._device.write(f"SOUR:WAVE:AMPL {value_to_write}")

    def get_wave_frequency(self) -> float:
        response = self._device.query(f"SOUR:WAVE:FREQ?")
        return float(response)

    def set_wave_duration(self, duration: Optional[float]) -> None:
        if duration is not None:
            duration_ = duration
        else:
            duration_ = "INF"
        self._device.write(f"SOUR:WAVE:DUR:TIME {duration_}")

    def get_wave_amplitude(self) -> float:
        response = self._device.query(f"SOUR:WAVE:AMPL?")
        coefficient_to_effective_current = (1 / 2) ** 0.5
        return float(response) * coefficient_to_effective_current

    def set_wave_frequency(self, frequency: float) -> None:
        self._device.write(f"SOUR:WAVE:FREQ {frequency}")

    def get_delta_2182_presence(self) -> bool:
        """
        Queries connection to 2182A.
        1 = yes, 0 = no
        TODO: maybe this function can be merged with @get_dcond_2182_presence
        """
        response = self._device.query("SOUR:DELT:NVPR?").strip()
        value = int(response)
        logger.info(f"Is NVPR? = [{response}]")
        return value > 0

    def get_dcond_2182_presence(self) -> bool:
        response = self._device.query("SOUR:DCON:NVPR?").strip()
        value = int(response)
        return value > 0

    def get_dcond_2182_query_rate(self) -> str:
        logger.warning(f"Command {self.get_dcond_2182_query_rate} is unsafe")
        self._device.write('SYST:COMM:SER:SEND "VOLT:NPLC?"')
        response = self._device.query("SYST:COMM:SER:ENT?").strip()
        logger.info(f"Keithley2182A(via 6221) query rate = [{response}]")
        self.get_error_status()
        return response

    def set_dcond_2182_query_rate(self, nplc: int) -> None:
        logger.warning(f"Command {self.set_dcond_2182_query_rate} is unsafe")
        self._device.write(f'SYST:COMM:SER:SEND "VOLT:NPLC {nplc}"')
        self.get_opc()
        self.get_error_status()

    def get_units(self) -> UNITS:
        response = self._device.query("UNIT:VOLT:DC?")
        value = response.strip()
        d: Dict[str, Keithley6221.UNITS] = {x.value: x for x in self.UNITS}
        return d[value]

    def set_units(self, units: UNITS) -> None:
        self._device.write(f"UNIT:VOLT:DC {units.value}")

    def get_dcond_arm_status(self) -> bool:
        response = self._device.query("DCON:ARM?").strip()
        value = int(response)
        return value > 0

    def get_delta_arm_status(self) -> bool:
        response = self._device.query("SOUR:DELT:ARM?").strip()
        value = int(response)
        logging.info(f"Delta ARM status = [{response}]")
        return value > 0

    def set_trace_points(self, buffer_size: int):
        self._device.write(f"TRACe:POINts {buffer_size}")

    def get_trace_data(self) -> List[float]:
        response = self._device.query(f"TRACe:DATA?").strip()
        numbers = response.split(",")
        result = [float(number) for number in numbers]
        logger.info(f"Response from trace = [{response}]")
        return result

    def get_trace_data_type(self, ):
        response = self._device.query("TRACe:DATA:TYPE?")
        logger.info(f"Response from trace_data_type= [{response}]")
        return response

    def get_trace_timestamp_format(self):
        response = self._device.query("TRACe:TSTamp:FORMat?")
        logger.info(f"Response from trace_timestamp_format= [{response}]")
        return response

    def get_trace_free_memory(self) -> str:
        response = self._device.query("TRACe:FREE?")
        logger.info(f"Response from trace_data_type= [{response}]")
        return response.strip()

    def get_trace_actual_data_points(self) -> int:
        response = self._device.query("TRACe:POINTs:ACTual?")
        logger.info(f"Response from trace_data_type= [{response}]")
        return int(response.strip())

    def get_display_window_1_text(self) -> str:
        response = self._device.query("DISP:WIND1:DATA?")
        return response.strip()

    def get_display_window_2_text(self) -> str:
        response = self._device.query("DISP:WIND2:DATA?")
        return response.strip()

    def close(self):
        logger.info(f"Trying to close Keithley6221 [{self._address}] ...")
        self._device.close()
        logger.info(f"Device Keithley6221 [{self._address}] is closed")

    def read_all_garbage_in_buffer(self):
        old_timeout = self._device.timeout
        try:
            self._device.timeout = 100 # 100ms
            for x in range(100):
                rem = self._device.read()
                logger.info(f"rem on {self._device_name}:[{rem}]")
        except Exception as e:
            logger.info(f"Skipping an exception on {self._device_name}: {str(e)}")
        finally:
            self._device.timeout = old_timeout
        # self.get_error_status()




if __name__ == "__main__":
    rm = pyvisa.ResourceManager()
    x = None

    try:
        address = "GPIB0::13::INSTR"
        dev = Keithley6221(address=address, rm=rm)
        print(dev.get_idn())
        start_current = -25e-6
        stop_current=25e-6
        step_size=0.1e-6
        delay=0.002
        delta=1e-6
        buffer_points: int = 60000
        ##############################################################################################
        estimated_time = ((stop_current - start_current) / step_size + 1) * (delay + 0.125) + 10
        dev.RunDifferentialConductanceMeasurements(
            start_current=start_current,
            stop_current=stop_current,
            step_size=step_size,
            delay=delay,
            delta=delta,
            buffer_points=buffer_points,
        )
        sleep_interval = 4.7
        time.sleep(sleep_interval + estimated_time)
        time_started = datetime.now()
        count = dev.get_trace_actual_data_points()
        print("Trace actual size", count)
        print("Trace buffer free size", dev.get_trace_free_memory())
        numbers = dev.get_trace_data()
        print(f"Trace length: {len(numbers)}")
        print(f"Trace numbers: ", numbers)
        points = [numbers[2 * i] for i in range(count)]
        currents = [start_current + i * step_size for i in range(points.__len__())]
        time_stamps = [numbers[2 * i + 1] for i in range(count)]
        print(f"Trace data type: {dev.get_trace_data_type()}")
        plt.plot(currents, points, "o")
        plt.show()
    except Exception as e:
        logging.exception("Handle it")
    finally:
        try:
            x.close()
        except:
            pass
        rm.close()
