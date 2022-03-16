# encoding: cp1251

from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np

import cfms.MSS_Control as MSS

import pyqtgraph.console
import pyqtgraph.dockarea

import pyvisa
import pyvisa.resources
import pyvisa.constants

import datetime
import sys
import os
import logging
import logging.handlers
import enum
import contextlib
import xmlrpc.server
import threading
import time

from typing import Optional


class Facility(enum.Enum):
    BLUEFORS = 0
    CFMS = 1
    STUDENT_INSERT = 2


# EXPERIMENT ===========================================================================================================

FACILITY = Facility.STUDENT_INSERT
SAMPLE = "HallSr-HallNa"
I = None
MEASURER_OBJECT = None
PROGRAM_OBJECT = None
MONITORING_OBJECT = None


# COMMANDS =============================================================================================================


def start():
    logging.info("USER COMMAND: start")

    global PROGRAM_OBJECT, I
    if PROGRAM_OBJECT is not None:
        logging.error("Program thread is already started! Stop it")
        return

    PROGRAM_OBJECT = Program()

    if not PROGRAM_OBJECT.check():
        logging.info("Syntax error in program!")
        del PROGRAM_OBJECT
        PROGRAM_OBJECT = None
        return

    I.status()
    PROGRAM_OBJECT.start()


def stop():
    logging.info("USER COMMAND: stop")

    global PROGRAM_OBJECT
    if PROGRAM_OBJECT is not None:
        PROGRAM_OBJECT.requestInterruption()
        PROGRAM_OBJECT.join(5)
        if PROGRAM_OBJECT.is_alive():
            logging.error("Error on waiting for PROGRAM_OBJECT to stop")
        del PROGRAM_OBJECT
        PROGRAM_OBJECT = None

    global MEASURER_OBJECT
    if MEASURER_OBJECT is not None:
        logging.info("Waiting for MEASURER to stop in up to 10 seconds...")
        MEASURER_OBJECT.requestInterruption()
        MEASURER_OBJECT.join(10)
        if MEASURER_OBJECT.is_alive():
            logging.error("Error on waiting for MEASURER_OBJECT to stop")
        del MEASURER_OBJECT
        MEASURER_OBJECT = None


def check():
    logging.info("USER COMMAND: check")

    global PROGRAM_OBJECT
    if PROGRAM_OBJECT is not None:
        logging.error("Program thread is already started! Stop it")
        return

    PROGRAM_OBJECT = Program()
    result = PROGRAM_OBJECT.check()
    PROGRAM_OBJECT = None

    return result


def status(all_thermometers=False):
    logging.info("USER COMMAND: status")

    if all_thermometers:
        I.status(all_thermometers=True)
    else:
        I.status()


# LOCKS ================================================================================================================

DEVICELOCK = threading.Lock()
CONSOLELOCK = threading.Lock()

# WINDOW SETTINGS ======================================================================================================

app = QtGui.QApplication([])
win = QtGui.QMainWindow()
area = pyqtgraph.dockarea.DockArea()
win.setCentralWidget(area)
win.setWindowTitle('Experiment2')
win.resize(1024, 768)

dock_prg = pyqtgraph.dockarea.Dock("Program")
dock_console = pyqtgraph.dockarea.Dock("Console")
dock_plot = pyqtgraph.dockarea.Dock("Graph")

area.addDock(dock_prg, "left")
area.addDock(dock_console, "bottom")
area.addDock(dock_plot, "right")

app.setStyleSheet("QTextEdit {font-family: Consolas}")

program_widget = QtGui.QTextEdit()
program_widget.setText("start-simple Test")

dock_prg.addWidget(program_widget)

console_widget = pyqtgraph.console.ConsoleWidget(
    namespace={"start": start, "stop": stop, "check": check, "status": status,
               "M": lambda: MEASURER_OBJECT, "I": lambda: I,
               "np": np})
dock_console.addWidget(console_widget)
layout = pg.GraphicsLayoutWidget()
dock_plot.addWidget(layout)

plotR = layout.addPlot(name="R", row=1, col=1)
plotPh = layout.addPlot(name="Ph", row=2, col=1)
plotPh.setXLink("R")
plotH = layout.addPlot(name="H", row=3, col=1)
plotH.setXLink("R")
plotT = layout.addPlot(name="T", row=4, col=1)
plotT.setXLink("R")

curveR1 = plotR.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(255, 0, 0))
curveR2 = plotR.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(0, 255, 0))
curveR3 = plotR.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(0, 0, 255))
curveR4 = plotR.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(255, 255, 255))
curveR5 = plotR.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(127, 127, 127))
curveR6 = plotR.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(255, 255, 255))
curveRK = plotR.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(255, 0, 0))
curveRUx = plotR.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(127, 127, 127))
curveRUy = plotR.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(0, 255, 0))
curveRUr = plotR.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(0, 0, 255))
curvePh1 = plotPh.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(255, 0, 0))
curvePh2 = plotPh.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(0, 255, 0))
curvePh3 = plotPh.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(0, 0, 255))
curvePh4 = plotPh.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(255, 255, 255))
curveH = plotH.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(255, 0, 0))
curveHall = plotH.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(0, 255, 0))
curveTsample1 = plotT.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(255, 0, 0))
curveTsample2 = plotT.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(0, 0, 128))
curveT1 = plotT.plot(symbol="o", pen=None, symbolPen=None, symbolSize=3, symbolBrush=pg.mkBrush(0, 0, 128))
curveT2 = plotT.plot(symbol="o", pen=None, symbolPen=None, symbolSize=3, symbolBrush=pg.mkBrush(0, 0, 255))
curveT3 = plotT.plot(symbol="o", pen=None, symbolPen=None, symbolSize=3, symbolBrush="g")
curveT5 = plotT.plot(symbol="o", pen=None, symbolPen=None, symbolSize=3, symbolBrush=pg.mkBrush(128, 0, 0))
curveT6 = plotT.plot(symbol="o", pen=None, symbolPen=None, symbolSize=3, symbolBrush=pg.mkBrush(255, 0, 0))
curveT7 = plotT.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(255, 0, 0))
curveT8 = plotT.plot(symbol="o", pen=None, symbolBrush=None, symbolSize=1, symbolPen=pg.mkPen(255, 0, 0))

win.show()


class ConsoleHandler(logging.Handler):
    def emit(self, record):
        str = self.format(record)
        # THIS SHIT CRASHES PYTHON SOMETIMES!
        # console_widget.write(str + "\n")


os.makedirs("log/", exist_ok=True)

logging.basicConfig(format="%(asctime)s - %(message)s",
                    level=logging.INFO,
                    handlers=[ConsoleHandler(),
                              logging.FileHandler(
                                  os.path.join("log", "log-{:%Y-%m-%d---%H-%M}.txt".format(datetime.datetime.today()))),
                              logging.StreamHandler(sys.stdout)])

R1_ANNOTATIONS_INDEX = 0
R2_ANNOTATIONS_INDEX = 0
R3_ANNOTATIONS_INDEX = 0
R4_ANNOTATIONS_INDEX = 0


def update_plots():
    global previous_time
    global MEASURER_OBJECT
    global R1_ANNOTATIONS_INDEX, R2_ANNOTATIONS_INDEX, R3_ANNOTATIONS_INDEX, R4_ANNOTATIONS_INDEX

    with CONSOLELOCK:
        if MEASURER_OBJECT is None:
            return
        try:
            MEASURER_OBJECT.TIME
        except AttributeError:
            return

        # The TIME array is always the largest
        number_of_points = len(MEASURER_OBJECT.TIME) - 1

        if number_of_points < 0:
            return

        # The maximum number of points per graph. Subsampling is used to decrease
        MAX_NUMBER_OF_POINTS = 10000
        SLICE_FACTOR = int(number_of_points / MAX_NUMBER_OF_POINTS) + 1

        if number_of_points > 10:
            deltat = MEASURER_OBJECT.TIME[-1] - MEASURER_OBJECT.TIME[-10]
            pps = 10 / deltat
            win.setWindowTitle(
                "Experiment2 - {} points (slice factor {}) - {:.1f} points per second".format(number_of_points,
                                                                                              SLICE_FACTOR, pps))

        if len(MEASURER_OBJECT.R_Sample) > 0:
            curveR1.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.R_Sample[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.R2) > 0:
            curveR2.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.R2[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.R3) > 0:
            curveR3.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.R3[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.R4) > 0:
            curveR4.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.R4[:number_of_points:SLICE_FACTOR])

        if len(MEASURER_OBJECT.RK) > 0:
            curveRK.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.RK[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.Ux) > 0:
            curveRUx.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.Ux[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.Uy) > 0:
            curveRUy.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.Uy[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.Ur) > 0:
            curveRUr.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.Ur[:number_of_points:SLICE_FACTOR])


        if len(MEASURER_OBJECT.PHASE1) > 0:
            curvePh1.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                             MEASURER_OBJECT.PHASE1[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.PHASE2) > 0:
            curvePh2.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                             MEASURER_OBJECT.PHASE2[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.PHASE3) > 0:
            curvePh3.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                             MEASURER_OBJECT.PHASE3[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.PHASE4) > 0:
            curvePh4.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                             MEASURER_OBJECT.PHASE4[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.Tetta) > 0:
            curvePh4.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                             MEASURER_OBJECT.Tetta[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.H) > 0:
            curveH.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                           MEASURER_OBJECT.H[:number_of_points:SLICE_FACTOR])
        if len(MEASURER_OBJECT.HALL) > 0:
            curveHall.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                              MEASURER_OBJECT.HALL[:number_of_points:SLICE_FACTOR])
        #
        if MEASURER_OBJECT.EXPERIMENT == "cooldown":
            curveT1.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.T1[:number_of_points:SLICE_FACTOR])
            curveT2.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.T2[:number_of_points:SLICE_FACTOR])
            curveT3.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.T3[:number_of_points:SLICE_FACTOR])
            curveT5.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.T5[:number_of_points:SLICE_FACTOR])
            curveT6.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.T6[:number_of_points:SLICE_FACTOR])
            curveT7.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.T7[:number_of_points:SLICE_FACTOR])
            curveT8.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                            MEASURER_OBJECT.T8[:number_of_points:SLICE_FACTOR])
        else:
            if len(MEASURER_OBJECT.Tsample1) > 0:
                curveTsample1.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                               MEASURER_OBJECT.Tsample1[:number_of_points:SLICE_FACTOR])
            if len(MEASURER_OBJECT.Tsample2) > 0:
                curveTsample2.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],
                               MEASURER_OBJECT.Tsample2[:number_of_points:SLICE_FACTOR])
            # Lots or errors if None in array!
            # if len(MEASURER_OBJECT.T7) > 0:
            #    curveT7.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],MEASURER_OBJECT.T7[:number_of_points:SLICE_FACTOR])
            # if len(MEASURER_OBJECT.T8) > 0:
            #    curveT8.setData(MEASURER_OBJECT.TIME[:number_of_points:SLICE_FACTOR],MEASURER_OBJECT.T8[:number_of_points:SLICE_FACTOR])

        while len(MEASURER_OBJECT.R1annotations) > R1_ANNOTATIONS_INDEX:
            x, y, status = MEASURER_OBJECT.R1annotations[R1_ANNOTATIONS_INDEX]
            annotate_u_plot(x, y, status)
            R1_ANNOTATIONS_INDEX += 1

        while len(MEASURER_OBJECT.R2annotations) > R2_ANNOTATIONS_INDEX:
            x, y, status = MEASURER_OBJECT.R2annotations[R2_ANNOTATIONS_INDEX]
            annotate_u_plot(x, y, status)
            R2_ANNOTATIONS_INDEX += 1

        while len(MEASURER_OBJECT.R3annotations) > R3_ANNOTATIONS_INDEX:
            x, y, status = MEASURER_OBJECT.R3annotations[R3_ANNOTATIONS_INDEX]
            annotate_u_plot(x, y, status)
            R3_ANNOTATIONS_INDEX += 1

        while len(MEASURER_OBJECT.R4annotations) > R4_ANNOTATIONS_INDEX:
            x, y, status = MEASURER_OBJECT.R4annotations[R4_ANNOTATIONS_INDEX]
            annotate_u_plot(x, y, status)
            R4_ANNOTATIONS_INDEX += 1


def annotate_u_plot(time, u, status):
    text = "\n".join(status)
    textitem = pg.TextItem(text, border="r")
    textitem.setPos(time, u)
    plotR.addItem(textitem)


update_timer = QtCore.QTimer()
update_timer.timeout.connect(update_plots)
update_timer.setInterval(1000)
update_timer.start()


# MEASUREMENTS =========================================================================================================


class Instruments:
    TC_CURRENT_EXC_LABELS = {
        1: "1 pA", 2: "3.16 pA", 3: "10 pA", 4: "31.6 pA", 5: "100 pA", 6: "316 pA",
        7: "1 nA", 8: "3.16 nA", 9: "10 nA", 10: "31.6 nA", 11: "100 nA", 12: "316 nA",
        13: "1 uA", 14: "3.16 uA", 15: "10 uA", 16: "31.6 uA", 17: "100 uA", 18: "316 uA",
        19: "1 mA", 20: "3.16 mA", 21: "10 mA", 22: "31.6 mA"
    }

    TC_CURRENT_RANGE_LABELS = {
        1: "2 mOhm", 2: "6.32 mOhm", 3: "20 mOhm", 4: "63.2 mOhm", 5: "200 mOhm", 6: "632 mOhm",
        7: "2 Ohm", 8: "6.32 Ohm", 9: "20 Ohm", 10: "63.2 Ohm", 11: "200 Ohm", 12: "632 Ohm",
        13: "2 kOhm", 14: "6.32 kOhm", 15: "20 kOhm", 16: "63.2 kOhm", 17: "200 kOhm", 18: "632 kOhm",
        19: "2 MOhm", 20: "6.32 MOhm", 21: "20 MOhm", 22: "63.2 MOhm"
    }

    TC_HEATER_RANGE_LABELS = {
        0: "Off", 1: "31.6 uA", 2: "100 uA", 3: "316 uA", 4: "1 mA", 5: "3.16 mA", 6: "10 mA", 7: "31.6 mA", 8: "100 mA"
    }

    TC_HEATER_RANGE_AMPS = {
        0: 0.0, 1: 31.6e-6, 2: 100e-6, 3: 316e-6, 4: 1e-3, 5: 3.16e-3, 6: 10e-3, 7: 31.6e-3, 8: 100e-3
    }

    CS580_GAIN_LABELS = {
        0: "1 nA/V", 1: "10 nA/V", 2: "100 nA/V", 3: "1 uA/V", 4: "10 uA/V", 5: "100 uA/V", 6: "1 mA/V", 7: "10 mA/V",
        8: "50 mA/V"
    }

    CS580_GAIN_AMPS = {
        0: 1e-9, 1: 10e-9, 2: 100e-9, 3: 1e-6, 4: 10e-6, 5: 100e-6, 6: 1e-3, 7: 10e-3, 8: 50e-3
    }

    def __init__(self):
        # If true, we consider the current source switched on and we can communicate with it
        self.CONFIG_MEASURE_FIELD = False
        # If false, the MXC temperature is measured. PT lower flange otherwise
        self.CONFIG_MEASURE_PT_FLANGE = False
        # If false, Yokogawa is used for gate handling
        self.CONFIG_GATE_AVAILABLE = False
        # If true, Keithley 2000 for HALL measuring is used
        self.CONFIG_MEASURE_HALL = False
        # If not None, Stanford research CS580 is used
        self.CONFIG_CS580_ADDRESS = None

        # If True, first lockin measures the current
        self.CONFIG_MEASURE_R1_CURRENT = False
        # If True, measure R2 from the second SR830
        self.CONFIG_MEASURE_R1 = False
        # If True, measure R2 from the second SR830
        self.CONFIG_MEASURE_R2 = False
        # If True, measure R3 from the third SR830
        self.CONFIG_MEASURE_R3 = False
        # If True, measure R4 from the third SR830
        self.CONFIG_MEASURE_R4 = False

        # Measure Keithley
        self.CONFIG_MEASURE_RK = False

        # Use Keithley6221
        self.CONFIG_MEASURE_KEITHLEY6221 = False

        # If True, measure R1 from the first Keithley2000
        self.CONFIG_MEASURE_Keithley_R1 = True
        # If True, measure T from channel A from the LakeShore
        self.CONFIG_MEASURE_LakeShore_T1 = True
        # If True, measure T from channel A and channel B from the LakeShore
        self.CONFIG_MEASURE_LakeShore_T2 = False
        # If True, measure Voltage from lockin
        self.CONFIG_MEASURE_Lockin = True
        logging.info("init_instruments")

        RM = pyvisa.ResourceManager()
        logging.info(RM.list_resources())

        if FACILITY == Facility.BLUEFORS:
            if self.CONFIG_CS580_ADDRESS is not None:
                self.CS580: pyvisa.resources.SerialInstrument = RM.open_resource(self.CONFIG_CS580_ADDRESS,
                                                                                 baud_rate=9600)

            if self.CONFIG_MEASURE_R1:
                self.R1: pyvisa.resources.SerialInstrument = RM.open_resource("ASRL3::INSTR",
                                                                              write_termination="\r",
                                                                              read_termination="\r",
                                                                              baud_rate=19200,
                                                                              parity=pyvisa.constants.Parity.even
                                                                              )
                # DONT DO IT! Several SR830 die after this command! (Error diode flashing continuously)
                # self.R1.clear()
                # Clear the status bits
                self.R1.write("*CLS")
            if self.CONFIG_MEASURE_R2:
                self.R2: pyvisa.resources.SerialInstrument = RM.open_resource("ASRL4::INSTR",
                                                                              write_termination="\r",
                                                                              read_termination="\r",
                                                                              baud_rate=19200,
                                                                              parity=pyvisa.constants.Parity.even)
                self.R2.write("*CLS")
            if self.CONFIG_MEASURE_R3:
                self.R3: pyvisa.resources.SerialInstrument = RM.open_resource("ASRL5::INSTR",
                                                                              write_termination="\r",
                                                                              read_termination="\r",
                                                                              baud_rate=19200,
                                                                              parity=pyvisa.constants.Parity.even)
                self.R3.write("*CLS")
            if self.CONFIG_MEASURE_R4:
                self.R4: pyvisa.resources.SerialInstrument = RM.open_resource("ASRL6::INSTR",
                                                                              write_termination="\r",
                                                                              read_termination="\r",
                                                                              baud_rate=19200,
                                                                              parity=pyvisa.constants.Parity.even)
                self.R4.write("*CLS")

            if self.CONFIG_MEASURE_RK:
                self.RK: pyvisa.resources.SerialInstrument = RM.open_resource("ASRL2::INSTR",
                                                                              write_termination="\r\n",
                                                                              read_termination="\r\n",
                                                                              baud_rate=57600,
                                                                              parity=pyvisa.constants.Parity.even,
                                                                              timeout=3000)

                self.RK.query("*RST; *OPC?")
                # Select ohms measurement function
                self.RK.query(":SENS:FUNC \"RES\"; *OPC?")
                # Set ohms mode (manual)
                self.RK.query(":SENS:RES:MODE MAN; *OPC?")
                # Enable offset compensation
                self.RK.query(":SENS:RES:OCOM ON; *OPC?")
                # Enable auto range
                self.RK.query(":SENS:RES:RANG:AUTO ON; *OPC?")

                # Select current mode
                self.RK.query(":SOUR:FUNC CURR; *OPC?")
                # Set current 1 nA
                self.RK.query(":SOUR:CURR:LEV:IMM:AMPL 1e-9; *OPC?")
                # ==================================================
                # Enable source delay auto mode
                self.RK.query(":SOUR:DEL:AUTO ON; *OPC?")

                # Disable source delay auto mode
                # self.RK.query(":SOUR:DEL:AUTO OFF; *OPC?")
                # Set source delay to 300 ms
                # self.RK.query(":SOUR:DEL 0.3; *OPC?")
                # ==================================================

                # Set integration time to 20 ms * 10 = 200 ms (high accuracy)
                self.RK.query(":SENS:RES:NPLC 10; *OPC?")

                # Enable auto filter
                self.RK.query(":SENS:AVER:AUTO ON; *OPC?")

                self.RK.query(":OUTP ON; *OPC?")

            if self.CONFIG_MEASURE_KEITHLEY6221:
                current: float = 1e-6
                delay: float = 10e-3
                count: Union[int, str] = "INF"
                swe_count: int = 1
                # init
                self.K6221: pyvisa.resources.GPIBInstrument = RM.open_resource("GPIB0::13::INSTR")
                """
                Эта функция запускать процесс измерения данных, но не хранит ничего в буфере.
                Это значит, что данные можно будет получать просто запросом -- get_delta_data или что-то в этом роде
                """
                # self.Abort()
                # time.sleep(2)
                enable_compliance_abort = self.ON_OFF_STATE.ON
                is_2182_ok = self.get_delta_2182_presence()
                if not is_2182_ok:
                    logger.warning("Cannot establish a connection between 6221 and 2182A via nul-modem cable")
                    return
                logger.info("Connection to keithley_2182a was established successfully!")
                if self.get_output_state():
                    logger.info("keithley_6221 output=ON detected. Turning it OFF.")
                    self.Abort()
                    time.sleep(2)
                    self.turn_output_off()
                    time.sleep(2)
                logger.info("Restore defaults")
                self.restore_defaults()
                self.get_error_status()
                logger.info("Set units to VOLTS")
                self.set_units(self.UNITS.Volts)
                self.get_error_status()
                logger.info("Query units")
                units = self.get_units()
                self.get_error_status()
                logger.info(f"Current units on keithley_6221 = [{units.value}]")
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
                # self.get_opc()
                self._device.write("SOUR:DELT:ARM")
                time.sleep(3)
                # self.get_opc()
                self.get_error_status()
                self._device.write("INIT:IMM")
                time.sleep(3)
                self.get_error_status()
                # # To disarm -- SOUR:SWE:ABOR

            # Intermagnetics
            if self.CONFIG_MEASURE_FIELD:
                self.H: pyvisa.resources.TCPIPSocket = RM.open_resource("TCPIP0::192.168.10.2::7180::SOCKET",
                                                                        read_termination="\r\n")

                # American Magnetics Model 430 IP Interface
                # self.H.read()
                # Hello.
                # self.H.read()

                # self.H = RM.open_resource("ASRL8::INSTR")
                # self.H.baud_rate = 115200

            if self.CONFIG_MEASURE_HALL:
                # Keithley2000
                # self.Hall = RM.open_resource("GPIB1::16::INSTR")
                pass

            # LakeShore
            self.T: pyvisa.resources.GPIBInstrument = RM.open_resource("GPIB0::12::INSTR")

            if self.CONFIG_GATE_AVAILABLE:
                # Yokogawa
                self.Vg = RM.open_resource("GPIB0::1::INSTR")

        elif FACILITY == Facility.CFMS:

            self.R1: pyvisa.resources.GPIBInstrument = RM.open_resource("GPIB0::8::INSTR")
            self.R1.write("*CLS")

            if self.CONFIG_MEASURE_R2:
                self.R2: pyvisa.resources.GPIBInstrument = RM.open_resource("GPIB0::9::INSTR")
                self.R2.write("*CLS")

            if self.CONFIG_MEASURE_R3:
                self.R3: pyvisa.resources.GPIBInstrument = RM.open_resource("GPIB0::3::INSTR")
                self.R3.write("*CLS")

            if self.CONFIG_MEASURE_R4:
                self.R4: pyvisa.resources.GPIBInstrument = RM.open_resource("GPIB0::3::INSTR")
                self.R4.write("*CLS")
            # self.T: pyvisa.resources.SerialInstrument = RM.open_resource("COM12",
            #                                                               write_termination="\r\n",
            #                                                               read_termination="\r\n",
            #                                                               baud_rate=57600,
            #                                                               parity=pyvisa.constants.Parity.odd,
            #                                                               data_bits=7)

        # I().T.query("*IDN?")
        elif FACILITY == Facility.STUDENT_INSERT:
            if self.CONFIG_MEASURE_Keithley_R1:
                self.Rsample: pyvisa.resources.GPIBInstrument = RM.open_resource("GPIB0::13::INSTR")
                self.Rsample.write("*CLS")

            if self.CONFIG_MEASURE_LakeShore_T1:
                self.LT1: pyvisa.resources.GPIBInstrument = RM.open_resource("GPIB0::14::INSTR")

            if self.CONFIG_MEASURE_LakeShore_T2:
                self.LT2: pyvisa.resources.GPIBInstrument = RM.open_resource("GPIB0::14::INSTR")
            if self.CONFIG_MEASURE_Lockin:
                self.Lockin: pyvisa.resources.SerialInstrument = RM.open_resource("GPIB0::8::INSTR")
                self.Lockin.write("*CLS")
        logging.info("init_instruments finished")

    def __del__(self):
        logging.info("deinit_instruments")

        if self.CONFIG_MEASURE_R1:
            self.R1.close()
        if self.CONFIG_MEASURE_R2:
            self.R2.close()
        if self.CONFIG_MEASURE_R3:
            self.R3.close()
        if self.CONFIG_MEASURE_R4:
            self.R4.close()
        if self.CONFIG_MEASURE_Keithley_R1:
            self.Rsample.close()
        if self.CONFIG_MEASURE_LakeShore_T1:
            self.LT1.close()
        if self.CONFIG_MEASURE_LakeShore_T2:
            self.LT2.close()
        if self.CONFIG_MEASURE_Lockin:
            self.Lockin.close()

        if FACILITY == Facility.BLUEFORS:
            if self.CONFIG_MEASURE_FIELD:
                self.H.close()

            if self.CONFIG_MEASURE_HALL:
                self.Hall.close()

            # TODO -- self._device.write("SOUR:WAVE:ABOR") for stoping  keithley 6221

            self.T.close()
            self.Vg.close()

        logging.info("deinit_instruments finished")

    def status(self, all_thermometers=False):

        def print_CS580(cs580: pyvisa.resources.MessageBasedResource):
            gain = int(cs580.query_ascii_values("GAIN?")[0])
            inpt = int(cs580.query_ascii_values("INPT?")[0])
            resp = int(cs580.query_ascii_values("RESP?")[0])
            shld = int(cs580.query_ascii_values("SHLD?")[0])
            isol = int(cs580.query_ascii_values("ISOL?")[0])
            sout = int(cs580.query_ascii_values("SOUT?")[0])
            return f"IN:{'ON' if inpt else 'OFF'} OUT:{'ON' if sout else 'OFF'} {self.CS580_GAIN_LABELS[gain]} SPD={'SLOW' if resp == 1 else 'FAST'} SHLD={'RETURN' if shld == 1 else 'GUARD'} ISOL={'FLOAT' if isol == 1 else 'GROUND'}"

        def print_SR830(sr830: pyvisa.resources.MessageBasedResource):
            u, phase = sr830.query_ascii_values("SNAP? 3,4")
            index, rangestr, value = self.get_range(sr830)
            indexrc, rcstr = self.get_rc(sr830)
            refindex, ref = self.get_reference_source(sr830)
            freq = self.get_frequency(sr830)
            amp = self.get_amplitude(sr830)
            srcindex, src = self.get_input_source(sr830)
            gnd = self.get_input_ground(sr830)[1]
            cpl = self.get_input_coupling(sr830)[1]
            flt = self.get_input_filters(sr830)[1]
            syncflt = self.get_sync_filter(sr830)[1]
            reserve = self.get_reserve(sr830)[1]

            offset, expand = sr830.query_ascii_values("OEXP? 3")
            expandstr = {0: "1x", 1: "10x", 2: "100x"}[int(expand)]

            result = "SRC(" + ref + "; " + str(amp) + "V; " + str(freq) + "Hz) "
            result += f"{src}; {gnd}; {cpl}; {flt}; sync {syncflt}"
            if srcindex in {0, 1}:
                # Volts
                result += f":{u / 1e-6:.3f} uV ({u / value * 100:.0f}% from {rangestr}, offset {offset:.0f}%, expand {expandstr}), phase {phase:.3f} deg, RC = {rcstr}, reserve = {reserve}"
            else:
                # Amperes
                result += f":{u / 1e-9:.3f} nA ({u / value * 100:.0f}% from {rangestr}, offset {offset:.0f}%, expand {expandstr}), phase {phase:.3f} deg, RC = {rcstr}, reserve = {reserve}"
            return result

        def print_Keithley6430(k: pyvisa.resources.MessageBasedResource) -> str:
            rk_v, rk_i, rk_r, rk_g1, rk_g2 = k.query_ascii_values(":READ?")
            result = f"Vsrc = {rk_v:.3f} V; Isrc = {rk_i * 1e9:.3f} nA; R = {rk_r:.3f} Ohm"
            return result

        if self.CONFIG_CS580_ADDRESS is not None:
            logging.info("CS580: " + print_CS580(self.CS580))

        if self.CONFIG_MEASURE_R1:
            logging.info("1: " + print_SR830(self.R1))
        if self.CONFIG_MEASURE_R2:
            logging.info("2: " + print_SR830(self.R2))
        if self.CONFIG_MEASURE_R3:
            logging.info("3: " + print_SR830(self.R3))
        if self.CONFIG_MEASURE_R4:
            logging.info("4: " + print_SR830(self.R4))

        if self.CONFIG_MEASURE_R1:
            logging.info("Current source parameters: {} V amplitude, {} Hz".format(self.get_amplitude(self.R1),
                                                                                   self.get_frequency(self.R1)))

        if self.CONFIG_MEASURE_RK:
            logging.info("Keithley6430: " + print_Keithley6430(self.RK))

        if self.CONFIG_GATE_AVAILABLE:
            function = self.get_gate_function()
            logging.info(f"Gate ENABLED and is functioning as '{function}' source")
            logging.info(f"Gate state is now {self.get_gate_state()}")
            logging.info(f"Protection current: {self.get_gate_protection_current()} A")
            logging.info(f"Protection voltage: {self.get_gate_protection_voltage()} V")
            if function == "volt":
                logging.info(f"Gate voltage: {self.get_gate_voltage()} V / {self.get_gate_range()} V")
            elif function == "curr":
                logging.info(f"Gate current: {self.get_gate_current()} A / {self.get_gate_range()} A")
            else:
                logging.warning("Unknown function!!!")

        if self.CONFIG_MEASURE_FIELD:
            logging.info(
                "Magnetic field (state {}): {:.1f} Oe -> {:.1f} Oe ({:.1f} Oe/min)".format(self.get_magnet_state(),
                                                                                           self.get_current_field() * 10000,
                                                                                           self.get_target_field() * 10000,
                                                                                           self.get_field_rate() * 10000))
        else:
            logging.info("Magnetic field not measured")

        logging.info("Current temperature is {:.3f} mK -> {:.3f} mK".format(self.get_temperature() * 1000,
                                                                            self.get_target_temperature() * 1000))

        if FACILITY == Facility.BLUEFORS:
            tc_mode = I.tc_mode()

            if tc_mode == 1:
                logging.info("TC in closed loop PID mode!")

                temp_ramp, temp_ramp_rate = self.get_temperature_ramp()
                if temp_ramp:
                    logging.info("Temperature ramp is ON with rate {:.3f} K/min".format(temp_ramp_rate))
                else:
                    logging.info("Temperature ramp is OFF")

                with DEVICELOCK:
                    channel, filter, units, delay, curpow, htrlim, htrres = [x.strip() for x in
                                                                             self.T.query("CSET?").split(",")]

                if int(curpow) != 2:
                    logging.info("Check LakeShore! The heater output not in power!")
                else:
                    htrres = float(htrres)  # Ohm

                    with DEVICELOCK:
                        # Get the heater value (unit is Watt)
                        htr = float(self.T.query("HTR?").strip())
                    htrrange, rangestr, maxcurrent = self.tc_get_heater_range()

                    maxpower = maxcurrent ** 2 * htrres

                    logging.info(
                        f"Heater emits {htr * 1000:.3f} mW / {maxpower * 1000:.3f} mW (max {maxcurrent * 1000:.3f} mA)")
            elif tc_mode == 3:
                logging.info("TC in open loop mode!")
                logging.info(f"Heater output is {I.tc_heater(log=False) * 1000000} uW")

            with DEVICELOCK:
                curchannel, autoscan = I.T.query_ascii_values("SCAN?")

            for channel in [1, 2, 3, 5, 6, 7, 8]:
                onoff, dwell, pause, curvenumber, tempcoeff = self.tc_get_channel_info(channel, log=False)
                with DEVICELOCK:
                    mode, excitation, rng, autorange, cs = I.T.query_ascii_values(f"RDGRNG? {channel}")
                    ohms, = I.T.query_ascii_values(f"RDGR? {channel}")
                    kelvins, = I.T.query_ascii_values(f"RDGK? {channel}")
                logging.info(
                    f"{channel}: {' ON' if onoff else 'OFF'}: DT {dwell:.1f} PT {pause:.1f} CN{curvenumber:02d} TC{tempcoeff}: {kelvins} K ({ohms} Ohm / {Instruments.TC_CURRENT_RANGE_LABELS[rng]}). Exc = {Instruments.TC_CURRENT_EXC_LABELS[excitation]} {'<====' if channel == curchannel else ''}")

            if all_thermometers:
                with DEVICELOCK:
                    curchannel, autoscan = [int(X) for X in self.T.query_ascii_values("SCAN?")]
                if autoscan:
                    logging.info("LakeShore: AUTOSCAN is ON")
                else:
                    logging.info("LakeShore: AUTOSCAN is OFF")
                for channel in [1, 2, 3, 5, 6]:
                    temp = self.get_temperature(channel)
                    if channel == curchannel:
                        logging.info("{}: {} K <======".format(channel, temp))
                    else:
                        logging.info("{}: {} K".format(channel, temp))

        if FACILITY == Facility.CFMS:
            logging.info("Rotator status: {}".format(self.get_rotator_state()))
            logging.info("Current angle: {}".format(self.get_current_angle()))

    def get_gate_state(self):
        if not self.CONFIG_GATE_AVAILABLE:
            logging.warning("Gate handling is DISABLED")
            return
        with DEVICELOCK:
            return self.Vg.query(":OUTP?").strip().lower()

    def set_gate_state(self, on):
        if not self.CONFIG_GATE_AVAILABLE:
            logging.warning("Gate handling is DISABLED")
            return
        with DEVICELOCK:
            self.Vg.write(f":OUTP {1 if on else 0}")

    def get_gate_function(self):
        if not self.CONFIG_GATE_AVAILABLE:
            logging.warning("Gate handling is DISABLED")
            return
        with DEVICELOCK:
            return self.Vg.query(":SOUR:FUNC?").strip().lower()

    def set_gate_function(self, function):
        if not self.CONFIG_GATE_AVAILABLE:
            logging.warning("Gate handling is DISABLED")
            return
        if not function in ["curr", "volt"]:
            logging.warning("Gate function can be only 'curr' or 'volt'")
            return
        with DEVICELOCK:
            self.Vg.write(f":SOUR:FUNC {function}")

    def get_gate_protection_voltage(self):
        if not self.CONFIG_GATE_AVAILABLE:
            logging.warning("Gate handling is DISABLED")
            return
        with DEVICELOCK:
            return self.Vg.query_ascii_values(":SOUR:PROT:VOLT?")[0]

    def get_gate_protection_current(self):
        if not self.CONFIG_GATE_AVAILABLE:
            logging.warning("Gate handling is DISABLED")
            return
        with DEVICELOCK:
            return self.Vg.query_ascii_values(":SOUR:PROT:CURR?")[0]

    def get_gate_range(self):
        if not self.CONFIG_GATE_AVAILABLE:
            logging.warning("Gate handling is DISABLED")
            return None
        with DEVICELOCK:
            # Returns voltage or current depending in function
            return self.Vg.query_ascii_values(":SOUR:RANG?")[0]

    def get_gate_voltage(self):
        if not self.CONFIG_GATE_AVAILABLE:
            logging.info("WARNING! Gate handling not available!")
            return None
            logging.warning("Gate is functioning in current mode!")
            return
        with DEVICELOCK:
            return self.Vg.query_ascii_values(":SOURCE:LEVEL?")

    def set_gate_voltage(self, voltage):
        if not self.CONFIG_GATE_AVAILABLE:
            logging.info("WARNING! Gate handling not available!")
            return
        if self.get_gate_function() != "volt":
            logging.warning("Gate is functioning in current mode!")
            return
        with DEVICELOCK:
            self.Vg.write(f":SOURCE:LEVEL {voltage}")

    def get_gate_current(self):
        if not self.CONFIG_GATE_AVAILABLE:
            logging.info("WARNING! Gate handling not available!")
            return None
        if self.get_gate_function() != "curr":
            logging.warning("Gate is functioning in voltage mode!")
            return
        with DEVICELOCK:
            return self.Vg.query_ascii_values(":SOURCE:LEVEL?")[0]

    def set_gate_current(self, current):
        if not self.CONFIG_GATE_AVAILABLE:
            logging.info("WARNING! Gate handling not available!")
            return
        if self.get_gate_function() != "curr":
            logging.warning("Gate is functioning in voltage mode!")
            return
        with DEVICELOCK:
            self.Vg.write(f":SOURCE:LEVEL {current}")

    def get_amplitude_and_theta(self, SR830) -> (float, float):
        # 1: X
        # 2: Y
        # 3: R
        # 4: theta
        with DEVICELOCK:
            return SR830.query_ascii_values("SNAP? 3,4")

    def get_reference_source(self, SR830) -> (int, str):
        try:
            with DEVICELOCK:
                index = int(SR830.query("FMOD?").strip())
        except ValueError:
            logging.info("Error parsing index from FMOD?")
            return None, None
        return (index, ["external", "internal"][index])

    def get_input_source(self, SR830) -> (int, str):
        try:
            with DEVICELOCK:
                index = int(SR830.query("ISRC?").strip())
        except ValueError:
            logging.info("Error parsing index from ISRC?")
            return None, None
        return (index, ["A", "A-B", "I(10^6)", "I(10^8)"][index])

    def get_input_ground(self, SR830) -> (int, str):
        try:
            with DEVICELOCK:
                index = int(SR830.query("IGND?").strip())
        except ValueError:
            logging.info("Error parsing index from IGND?")
            return None, None
        return (index, ["float", "ground"][index])

    def get_input_coupling(self, SR830) -> (int, str):
        try:
            with DEVICELOCK:
                index = int(SR830.query("ICPL?").strip())
        except ValueError:
            logging.info("Error parsing index from ICPL?")
            return None, None
        return (index, ["AC", "DC"][index])

    def get_input_filters(self, SR830) -> (int, str):
        try:
            with DEVICELOCK:
                index = int(SR830.query("ILIN?").strip())
        except ValueError:
            logging.info("Error parsing index from ILIN?")
            return None, None
        return (index, ["no filters", "1x notch", "2x notch", "both notch"][index])

    def get_sync_filter(self, SR830) -> (int, str):
        try:
            with DEVICELOCK:
                index = int(SR830.query("SYNC?").strip())
        except ValueError:
            logging.info("Error parsing index from SYNC?")
            return None, None
        return (index, {0: "off", 1: "on"}[index])

    def get_status(self, SR830):
        try:
            with DEVICELOCK:
                b = SR830.query_ascii_values("LIAS?", converter="d")[0]
        except ValueError:
            logging.info("Error parsing status from LIAS? for {}".format(SR830))
            return set()
        errors = set()
        if b & 0x01 != 0:
            errors |= {"I/S"}
        if b & 0x02 != 0:
            errors |= {"TC"}
        if b & 0x04 != 0:
            errors |= {"OUT"}
        return errors

    def get_reserve(self, SR830) -> (int, str):
        try:
            with DEVICELOCK:
                index = int(SR830.query("RMOD?").strip())
        except ValueError:
            logging.info("Error parsing index from RMOD?")
            return None, None
        return (index, ["high reserve", "normal reserve", "low noise"][index])

    def get_range(self, SR830) -> (int, str, float):
        try:
            with DEVICELOCK:
                index = int(SR830.query("SENS?").strip())
        except ValueError:
            logging.info("Error parsing index from SENS?")
            return None, None, None
        ranges = [("2 nV", 2e-9), ("5 nV", 5e-9), ("10 nV", 10e-9),
                  ("20 nV", 20e-9), ("50 nV", 50e-9), ("100 nV", 100e-9),
                  ("200 nV", 200e-9), ("500 nV", 500e-9), ("1 uV", 1e-6),
                  ("2 uV", 2e-6), ("5 uV", 5e-6), ("10 uV", 10e-6),
                  ("20 uV", 20e-6), ("50 uV", 50e-6), ("100 uV", 100e-6),
                  ("200 uV", 200e-6), ("500 uV", 500e-6),
                  ("1 mV", 1e-3), ("2 mV", 2e-3), ("5 mV", 5e-3),
                  ("10 mV", 10e-3), ("20 mV", 20e-3), ("50 mV", 50e-3),
                  ("100 mV", 100e-3), ("200 mV", 200e-3), ("500 mV", 500e-3),
                  ("1 V", 1.0)]
        return index, ranges[index][0], ranges[index][1]

    def set_range(self, SR830, range_txt, dryrun=False):
        try:
            range_index = ["2nV", "5nV", "10nV", "20nV", "50nV", "100nV", "200nV", "500nV", "1uV", "2uV", "5uV", "10uV",
                           "20uV", "50uV", "100uV", "200uV", "500uV", "1mV", "2mV", "5mV", "10mV", "20mV", "50mV",
                           "100mV", "200mV", "500mV", "1V"].index(range_txt)
        except ValueError:
            logging.info("Cannot find {} in list".format(range_txt))
            return False

        if not dryrun:
            with DEVICELOCK:
                SR830.write("SENS {}".format(range_index))
        return True

    def range_up(self, SR830):
        index, str, value = self.get_range(SR830)
        if index < 26:
            with DEVICELOCK:
                SR830.write("SENS {}".format(index + 1))

    def range_down(self, SR830):
        index, str, value = self.get_range(SR830)
        if index > 0:
            with DEVICELOCK:
                SR830.write("SENS {}".format(index - 1))

    def get_rc(self, SR830) -> (int, str):
        try:
            with DEVICELOCK:
                index = int(SR830.query("OFLT?").strip())
        except ValueError:
            logging.info("Error parsing index from OFLT?")
            return None, None
        rcs = ["10 us", "30 us", "100 us", "300 us", "1 ms", "3 ms", "10 ms", "30 ms", "100 ms", "300 ms",
               "1 s", "3 s", "10 s", "30 s", "100 s", "300 s", "1 ks", "3 ks", "10 ks", "30 ks"]
        return index, rcs[index]

    def rc_up(self, SR830):
        index, str = self.get_rc(SR830)
        if index < 19:
            with DEVICELOCK:
                SR830.write("OFLT {}".format(index + 1))

    def rc_down(self, SR830):
        index, str = self.get_rc(SR830)
        if index > 0:
            with DEVICELOCK:
                SR830.write("OFLT {}".format(index - 1))

    def get_amplitude(self, SR830):
        with DEVICELOCK:
            current_amp, = SR830.query_ascii_values("SLVL?")
        return current_amp

    def set_amplitude(self, SR830, amplitude):
        with DEVICELOCK:
            SR830.write("SLVL {}".format(amplitude))

    def get_frequency(self, SR830):
        with DEVICELOCK:
            current_freq, = SR830.query_ascii_values("FREQ?")
        return current_freq

    def set_frequency(self, SR830, frequency):
        with DEVICELOCK:
            SR830.write("FREQ {}".format(frequency))

    def set_offset_expand_on(self, SR830, mult):
        if mult not in ("1x", "10x", "100x"):
            logging.warning("Only 1x or 10x or 100x mult is allowed!")
            return

        with DEVICELOCK:
            SR830.write("AOFF 3")
            offset, expand = SR830.query_ascii_values("OEXP? 3")
            # Arg1: 1 - X, 2 - Y, 3 - R
            # Arg2: offset in percent
            # Arg3: 0 - 0, 1 - 10, 2 - 100
            multstr = {"1x": 0, "10x": 1, "100x": 2}[mult]
            SR830.write(f"OEXP 3,{offset},{multstr}")
            return offset

    def set_offset_expand_off(self, SR830):
        with DEVICELOCK:
            SR830.write("OEXP 3,0,0")

    def get_current_field(self):
        if FACILITY == Facility.BLUEFORS:
            # FIELD:MAGNET?
            with DEVICELOCK:
                field, = self.H.query_ascii_values("FIELD:MAG?")
        elif FACILITY == Facility.CFMS:
            with DEVICELOCK:
                field = MSS.get_platform_signal()[0]
        return field

    def get_target_field(self):
        if FACILITY == Facility.BLUEFORS:
            # FIELD:TARGET?
            with DEVICELOCK:
                field, = self.H.query_ascii_values("FIELD:TARG?")
        elif FACILITY == Facility.CFMS:
            logging.warning("NOT IMPLEMENTED")
            field = 0
        return field

    def set_target_field(self, field_in_T, rate_in_Tpermin):
        if FACILITY == Facility.BLUEFORS:
            with DEVICELOCK:
                self.H.write("CONFIGURE:RAMP:RATE:FIELD 1,{},1;".format(rate_in_Tpermin))
                self.H.write("CONFIGURE:FIELD:TARGET {};".format(field_in_T))
        elif FACILITY == Facility.CFMS:
            with DEVICELOCK:
                MSS.set_field(field_in_T, rate_in_Tpermin)

    def get_field_rate(self) -> float:
        if FACILITY == Facility.BLUEFORS:
            with DEVICELOCK:
                rate, limit = self.H.query_ascii_values("RAMP:RATE:FIELD:1?")
        elif FACILITY == Facility.CFMS:
            with DEVICELOCK:
                rate = MSS.get_ramp_rate()[0]  # Tesla per minute
            return rate
        return rate

    def get_magnet_state(self):
        if FACILITY == Facility.BLUEFORS:
            try:
                with DEVICELOCK:
                    state = int(self.H.query("STATE?").strip())
            except ValueError:
                logging.info("Error parsing state!")
                return None

            state_dict = {
                1: "RAMP",
                2: "HOLD",
                3: "PAUSED",
                4: "MANUAL UP",
                5: "MANUAL DOWN",
                6: "ZEROING CURRENT",
                7: "QUENCH DETECTED",
                8: "ZERO",
                9: "HEATING SWITCH",
                10: "COOLING SWITCH"
            }

            try:
                return state_dict[state]
            except KeyError:
                return "UNKNOWN STATE (" + str(str) + ")"

        elif FACILITY == Facility.CFMS:
            with DEVICELOCK:
                ramping = not MSS.get_SMS_ramp_status()
            if ramping:
                return "RAMPING"
            else:
                return "NOT RAMPING"

    def get_magnet_ramping(self) -> bool:
        status = self.get_magnet_state()

        if FACILITY == Facility.BLUEFORS:
            return (status == "RAMP")
        elif FACILITY == Facility.CFMS:
            return (status == "RAMPING")

    def ramp(self):
        with DEVICELOCK:
            self.H.write("RAMP")

    def zero(self):
        with DEVICELOCK:
            self.H.write("ZERO")

    def quench_clear(self):
        with DEVICELOCK:
            self.H.write("QU 0")

    def tc_get_heater_range(self) -> (int, str, float):
        if FACILITY == Facility.BLUEFORS:
            try:
                with DEVICELOCK:
                    index = int(self.T.query("HTRRNG?").strip())
            except ValueError:
                logging.info("Error parsing index from HTRRNG?")
                return None, None, None
            return index, Instruments.TC_HEATER_RANGE_LABELS[index], Instruments.TC_HEATER_RANGE_AMPS[index]
        elif FACILITY == Facility.CFMS:
            logging.warning("NOT IMPLEMENTED")
            return 0, "N/I", 0

    def tc_heater_range_up(self):
        htrrange = self.tc_get_heater_range()[0]
        if htrrange < 8:
            with DEVICELOCK:
                self.T.write("HTRRNG {}".format(htrrange + 1))
                logging.info(f"TC heater range is set to {Instruments.TC_HEATER_RANGE_LABELS[htrrange + 1]}")

    def tc_heater_range_down(self):
        htrrange = self.tc_get_heater_range()[0]
        if htrrange > 0:
            with DEVICELOCK:
                self.T.write("HTRRNG {}".format(htrrange - 1))
                logging.info(f"TC heater range is set to {Instruments.TC_HEATER_RANGE_LABELS[htrrange - 1]}")

    def tc_heater_range_max(self):
        with DEVICELOCK:
            self.T.write("HTRRNG 8")
            logging.info(f"TC heater range is set to {Instruments.TC_HEATER_RANGE_LABELS[8]}")

    def get_target_temperature(self):
        if FACILITY == Facility.BLUEFORS:
            with DEVICELOCK:
                temp_in_kelvin = float(self.T.query_ascii_values("SETP?")[0])
        elif FACILITY == Facility.CFMS:
            logging.warning("NOT IMPLEMENTED (AND WILL NEVER BE)")
            temp_in_kelvin = 0
        elif FACILITY == Facility.STUDENT_INSERT:
            logging.warning("NOT IMPLEMENTED (AND WILL NEVER BE)")
            temp_in_kelvin = 0
        return temp_in_kelvin

    def set_target_temperature(self, temp_in_kelvin, ramp_in_mK_per_min=None):
        with DEVICELOCK:
            if FACILITY == Facility.BLUEFORS:
                if ramp_in_mK_per_min is not None:
                    self.T.write(f"RAMP 1,{ramp_in_mK_per_min * 0.001}")
                else:
                    self.T.write(f"RAMP 0,0")

                # Need a pause. LakeShore 370, hello!
                time.sleep(0.5)

                self.T.write(f"SETP {temp_in_kelvin}")
            elif FACILITY == Facility.CFMS:
                MSS.set_temperature(temp_in_kelvin, ramp_in_mK_per_min * 0.001)

    def get_temperature(self, channel=None):
        with DEVICELOCK:
            if FACILITY == Facility.BLUEFORS:
                if channel is None:
                    if self.CONFIG_MEASURE_PT_FLANGE:
                        return I.T.query_ascii_values("RDGK? 2")[0]
                    else:
                        return I.T.query_ascii_values("RDGK? 6")[0]
                else:
                    return I.T.query_ascii_values("RDGK? " + str(channel))[0]

            elif FACILITY == Facility.CFMS:
                # return I.T.query_ascii_values("KRDG? A")[0]
                return MSS.get_temperature_B()[0]

            elif FACILITY == Facility.STUDENT_INSERT:
                return I.LT1.query_ascii_values("KRDG? A")[0]

    def get_temperature_ramp(self):
        with DEVICELOCK:
            if FACILITY == Facility.BLUEFORS:
                try:
                    Q = self.T.query_ascii_values("RAMP?")
                    ramp, rate = bool(Q[0]), float(Q[1])
                except IndexError:
                    logging.info("Error parsing self.T.query('RAMP?')")
                    return 0, 0
            elif FACILITY == Facility.CFMS:
                logging.warning("NOT IMPLEMENTED (AND WILL NEVER BE)")
                ramp, rate = 0, 0
            return ramp, rate

    def get_temperature_ramping(self):
        with DEVICELOCK:
            if FACILITY == Facility.BLUEFORS:
                return bool(I.T.query_ascii_values("RAMPST?")[0])
            elif FACILITY == Facility.CFMS:
                logging.warning("NOT IMPLEMENTED")
                ramping = False
            return ramping

    def select_channel(self, channel, autoscan):
        with DEVICELOCK:
            self.T.write("SCAN {},{}".format(channel, autoscan))

    def get_tc_channel(self):
        with DEVICELOCK:
            # Returned:
            #     <channel>, <autoscan>[term]
            return int(I.T.query_ascii_values("SCAN?")[0])

    def tc_range(self):
        current_channel = self.get_tc_channel()
        with DEVICELOCK:
            mode, excitation, rng, autorange, cs = I.T.query_ascii_values(f"RDGRNG? {current_channel}")
            logging.info(f"TC range for channel {current_channel} is {self.TC_CURRENT_RANGE_LABELS[rng]}")

    def tc_range_up(self):
        current_channel = self.get_tc_channel()
        with DEVICELOCK:
            mode, excitation, rng, autorange, cs = I.T.query_ascii_values(f"RDGRNG? {current_channel}")
            if rng < 22:
                I.T.write(f"RDGRNG {current_channel},{mode},{excitation},{rng + 1},{autorange},{cs}")
                logging.info(f"Setting TC range to {self.TC_CURRENT_RANGE_LABELS[rng + 1]}")

    def tc_range_down(self):
        current_channel = self.get_tc_channel()
        with DEVICELOCK:
            mode, excitation, rng, autorange, cs = I.T.query_ascii_values(f"RDGRNG? {current_channel}")
            if rng > 1:
                I.T.write(f"RDGRNG {current_channel},{mode},{excitation},{rng - 1},{autorange},{cs}")
                logging.info(f"Setting TC range to {self.TC_CURRENT_RANGE_LABELS[rng - 1]}")

    def tc_current(self):
        current_channel = self.get_tc_channel()
        with DEVICELOCK:
            mode, excitation, rng, autorange, cs = I.T.query_ascii_values(f"RDGRNG? {current_channel}")
            logging.info(f"TC current for channel {current_channel} is {self.TC_CURRENT_EXC_LABELS[excitation]}")

    def tc_current_up(self):
        current_channel = self.get_tc_channel()
        with DEVICELOCK:
            mode, excitation, rng, autorange, cs = I.T.query_ascii_values(f"RDGRNG? {current_channel}")
            if excitation < 22:
                I.T.write(f"RDGRNG {current_channel},{mode},{excitation + 1},{rng},{autorange},{cs}")
                logging.info(f"Setting TC current to {self.TC_CURRENT_EXC_LABELS[excitation + 1]}")

    def tc_current_down(self):
        current_channel = self.get_tc_channel()
        with DEVICELOCK:
            mode, excitation, rng, autorange, cs = I.T.query_ascii_values(f"RDGRNG? {current_channel}")
            if excitation > 1:
                I.T.write(f"RDGRNG {current_channel},{mode},{excitation - 1},{rng},{autorange},{cs}")
                logging.info(f"Setting TC current to {self.TC_CURRENT_EXC_LABELS[excitation - 1]}")

    def tc_heater(self, heat_in_uwatt=None, log=True):
        with DEVICELOCK:
            if heat_in_uwatt is None:
                power = I.T.query_ascii_values("MOUT?")[0]
                if log:
                    logging.info(f"Manual TC heater is {power / 1e-6} uW")
                return power
            else:
                I.T.write(f"MOUT {heat_in_uwatt * 1e-6}")

    def tc_mode(self, mode=None):
        with DEVICELOCK:
            if mode is None:
                mode = int(I.T.query_ascii_values("CMODE?")[0])
                modestr = {1: "Closed loop PID", 2: "Zone Tuning", 3: "Open Loop", 4: "Off"}[mode]
                logging.info(f"TC mode is {mode} ({modestr})")
                return mode
            else:
                I.T.write(f"CMODE {mode}")

    def tc_get_channel_info(self, channel: int, log=True):
        with DEVICELOCK:
            onoff, dwell, pause, curvenumber, tempcoeff = I.T.query_ascii_values(f"INSET? {channel}", converter="s")
            onoff, dwell, pause, curvenumber, tempcoeff = int(onoff), float(dwell), float(pause), int(curvenumber), int(
                tempcoeff)
            if log:
                logging.info(
                    f"TC channel {channel}: {'ON' if onoff else 'OFF'}, dwell time = {dwell}, pause time = {pause}, curvenumber = {curvenumber}, tempcoeff = {tempcoeff}")
            return onoff, dwell, pause, curvenumber, tempcoeff

    def tc_channel_off(self, channel: int):
        onoff, dwell, pause, curvenumber, tempcoeff = self.tc_get_channel_info(channel)
        with DEVICELOCK:
            logging.info(f"TC: turning channel {channel} OFF")
            I.T.write(f"INSET {channel},0,{dwell},{pause},{curvenumber},{tempcoeff}")

    def tc_channel_on(self, channel: int):
        onoff, dwell, pause, curvenumber, tempcoeff = self.tc_get_channel_info(channel)
        with DEVICELOCK:
            logging.info(f"TC: turning channel {channel} ON")
            I.T.write(f"INSET {channel},1,{dwell},{pause},{curvenumber},{tempcoeff}")

    def get_current_angle(self):
        with DEVICELOCK:
            if FACILITY == Facility.BLUEFORS:
                logging.warning("NOT IMPLEMENTED")
            elif FACILITY == Facility.CFMS:
                return MSS.get_angle()[0]

    def set_target_angle(self, angle_deg, rate_deg_per_min):
        with DEVICELOCK:
            MSS.start_rotation(angle_deg, rate_deg_per_min)

    def get_rotator_state(self):
        with DEVICELOCK:
            return MSS.get_rotator_status()


class DiDvMeasurer(threading.Thread):
    def __init__(self):
        super().__init__()

        self.TIME = []
        self.R1, self.PHASE1, self.R1annotations = [], [], []
        self.R2, self.PHASE2, self.R2annotations = [], [], []
        self.R3, self.PHASE3, self.R3annotations = [], [], []
        self.R4, self.PHASE4, self.R4annotations = [], [], []
        self.RK = []
        self.R5, self.R6 = [], []
        self.H, self.HALL = [], []
        self.T, self.Tsample = [], []
        self.T1, self.T2, self.T3, self.T5, self.T6 = [], [], [], [], []
        self.T7, self.T8 = [], []

        self.START_TIME = time.perf_counter()

        self.current_start = None
        self.current_finish = None
        self.numsteps = None
        self.current_delta = None

        self.stopped = False
        self.sample = None
        self.name = None

    def init_files(self, sample, name):
        dirname = "{:%Y-%m-%d}".format(datetime.datetime.today())
        data_filename = "{:%Y%m%d-%H%M}-{sample}-{name}-didv.txt".format(datetime.datetime.today(), sample=sample,
                                                                         name=name)

        os.makedirs(os.path.join("data", dirname), exist_ok=True)

        self.data_filename = os.path.join("data", dirname, data_filename)
        self.datafile = open(self.data_filename, "wt")

    def write_header(self):
        P = ["I", "time", "dV/dI"]
        U = ["A", "seconds", "Ohm"]
        self.datafile.write("\t".join(P) + "\n")
        self.datafile.write("\t".join(U) + "\n")
        self.datafile.flush()

    def write_data(self, I_amps, time_seconds, dVdI_ohms):
        D = [I_amps, time_seconds, dVdI_ohms]
        self.datafile.write("\t".join([str(x) for x in D]) + "\n")
        self.datafile.flush()

    def run(self):
        logging.info("DiDvMeasurer: Measurements started")

        self.init_files(self.sample, self.name)

        I.K6221.write("*RST")
        # Possible values: V, OHMS, W, SIEM
        I.K6221.write("UNIT OHMS")

        I.K6221.write(f"SOUR:DCON:STAR {self.current_start}")
        I.K6221.write(f"SOUR:DCON:STOP {self.current_finish}")

        self.current_step = (self.current_finish - self.current_start) / self.numsteps
        I.K6221.write(f"SOUR:DCON:STEP {self.current_step}")
        I.K6221.write(f"SOUR:DCON:DELT {self.current_delta}")
        I.K6221.write(f"SOUR:DCON:DEL 50e-3")  # 50 ms

        I.K6221.write(f"SOUR:DCON:CAB OFF")  # Don't abort on complience

        I.K6221.write(f"TRAC:POIN {self.numsteps}")
        I.K6221.write(f"SOUR:DCON:ARM")
        time.sleep(3)

        logging.info("DiDvMeasurer: Arming...")

        while int(I.K6221.query(f"SOUR:DCON:ARM?")) == 0:
            time.sleep(0.5)

        logging.info("DiDvMeasurer: Armed.")

        I.K6221.write("INIT:IMM")
        time.sleep(3)

        while not self.stopped:
            time.sleep(1)
            status = int(I.K6221.query("STAT:OPER:COND?"))
            bit_calibrating = bool(status & 0b0001)
            bit_sweepdone = bool(status & 0b0010)
            bit_sweeping = bool(status & 0b1000)
            logging.info(
                f"status={status} (calibrating = {bit_calibrating}, sweepdone = {bit_sweepdone}, sweeping = {bit_sweeping})")

            if bit_sweepdone:
                break

        self.zero_voltage = I.K6221.query_ascii_values(f"SOUR:DCON:NVZ?")[0]
        logging.info(f"DiDvMeasurer: Zero voltage = {self.zero_voltage} V")

        self.write_header()
        self.data = I.K6221.query_ascii_values("TRAC:DATA?")
        for index, (ohm, t) in enumerate(zip(self.data[::2], self.data[1::2])):
            self.write_data(index * self.current_step + self.current_start, t, ohm)

        I.K6221.write(f"SOUR:SWE:ABOR")

        logging.info("DiDvMeasurer: Measurements stopped")
        self.stopped = True

    def requestInterruption(self):
        self.stopped = True


class Measurer(threading.Thread):
    def __init__(self):
        logging.info("MEASURER: __init__")

        super().__init__()

        logging.info("MEASURER: After __init__")

        # self.EXPERIMENT = "simple" # Just measure data non-stop
        # self.EXPERIMENT = "cooldown" # Just measure data non-stop
        # self.EXPERIMENT = "step" # Make step -> Wait for relaxation -> Measure -> Repeat it from step 1.

        # self.STEP_VALUE = "VG"
        # self.STEP_RELAX_TIME = 3.000
        # self.STEP_MEASURE_TIME = 27.000
        # self.STEP_LIST = list(np.linspace(5, 3, 100))
        self.STEP_LASTTIME = None
        self.STEP_FIRSTPOINT = None

        self.TIME = []
        self.R1, self.PHASE1, self.R1annotations = [], [], []
        self.R2, self.PHASE2, self.R2annotations = [], [], []
        self.R3, self.PHASE3, self.R3annotations = [], [], []
        self.R4, self.PHASE4, self.R4annotations = [], [], []
        self.RK = []
        self.R5, self.R6 = [], []
        self.H, self.HALL = [], []
        self.T, self.Tsample1, self.Tsample2 = [], [], []
        self.T1, self.T2, self.T3, self.T5, self.T6 = [], [], [], [], []
        self.T7, self.T8 = [], []
        self.R_Sample = []
        self.Ux, self.Uy, self.Ur, self.Tetta = [], [], [], []
        self.START_TIME = time.perf_counter()

        self.AUTORANGE = True

        self.stopped = False
        self.sample = None
        self.EXPERIMENT = None

    def init_files(self, sample, name):
        dirname = "{:%Y-%m-%d}".format(datetime.datetime.today())
        data_filename = "{:%Y%m%d-%H%M}-{sample}-{name}.txt".format(datetime.datetime.today(), sample=sample, name=name)
        proc_filename = "{:%Y%m%d-%H%M}-{sample}-{name}-proc.txt".format(datetime.datetime.today(), sample=sample,
                                                                         name=name)

        os.makedirs(os.path.join("data", dirname), exist_ok=True)

        self.data_filename = os.path.join("data", dirname, data_filename)
        self.datafile = open(self.data_filename, "wt")
        self.proc_filename = os.path.join("data", dirname, proc_filename)
        self.procfile = open(self.proc_filename, "wt")

    def write_header(self):
        if I.CONFIG_MEASURE_R1_CURRENT:
            C1, U1 = "I1", "A"
        else:
            C1, U1 = "U1", "V"
        P = ["time", 'C1', "Phase1", "U2", "Phase2", "U3", "Phase3", "U4", "Phase4", "H", "Hall", "T", "T7", "T8", "RK",
             'T_Sample_1', 'T_Sample_2', 'R_Sample', 'Ux', 'Uy', 'Ur', 'Tetta']
        U = ["seconds", 'U1', "degrees", "V", "degrees", "V", "degrees", "V", "degrees", "T", "Ohm", "K", "Ohm", "Ohm",
             "Ohm", 'K', 'K', "Ohm", 'V', 'V', 'V', 'degrees']
        self.datafile.write("\t".join(P) + "\n")
        self.datafile.write("\t".join(U) + "\n")
        self.datafile.flush()

    def write_data(self, time_secs, U1_volts, Phase1_degrees, U2_volts, Phase2_degrees, U3_volts, Phase3_degrees,
                   U4_volts, Phase4_degrees, H_T, Hall_volts, T_K, T7_Ohm, T8_Ohm, RK_Ohm, T_Sample1_K, T_Sample2_K,
                   R_Sample_Ohm, X_V, Y_V, R_V, Tetta_degrees):
        D = [time_secs, U1_volts, Phase1_degrees, U2_volts, Phase2_degrees, U3_volts, Phase3_degrees, U4_volts,
             Phase4_degrees, H_T, Hall_volts, T_K, T7_Ohm, T8_Ohm, RK_Ohm, T_Sample1_K, T_Sample2_K, R_Sample_Ohm, X_V,
             Y_V, R_V, Tetta_degrees]
        self.datafile.write("\t".join([str(x) for x in D]) + "\n")
        self.datafile.flush()

    def write_header_cooldown(self):
        if I.CONFIG_MEASURE_R1_CURRENT:
            P = ["time", "I1", "Phase1", "U2", "Phase2", "U3", "Phase3", "U4", "Phase4", "H", "Hall", "T1", "T2", "T3",
                 "T5", "T6", "T7", "T8"]
            U = ["seconds", "I", "degrees", "V", "degrees", "V", "degrees", "V", "degrees", "T", "Ohm", "K", "K", "K",
                 "K", "K", "Ohm", "Ohm"]
        else:
            P = ["time", "U1", "Phase1", "U2", "Phase2", "U3", "Phase3", "U4", "Phase4", "H", "Hall", "T1", "T2", "T3",
                 "T5", "T6", "T7", "T8"]
            U = ["seconds", "V", "degrees", "V", "degrees", "V", "degrees", "V", "degrees", "T", "Ohm", "K", "K", "K",
                 "K", "K", "Ohm", "Ohm"]
        self.datafile.write("\t".join(P) + "\n")
        self.datafile.write("\t".join(U) + "\n")
        self.datafile.flush()

    def write_data_cooldown(self, time_secs, U1_volts, Phase1_degrees, U2_volts, Phase2_degrees, U3_volts,
                            Phase3_degrees, U4_volts, Phase4_degrees, H_T, Hall_volts, T1_K, T2_K, T3_K, T5_K, T6_K,
                            T7_Ohm, T8_Ohm):
        D = [time_secs, U1_volts, Phase1_degrees, U2_volts, Phase2_degrees, U3_volts, Phase3_degrees, U4_volts,
             Phase4_degrees, H_T, Hall_volts, T1_K, T2_K, T3_K, T5_K, T6_K, T7_Ohm, T8_Ohm]
        self.datafile.write("\t".join([str(x) for x in D]) + "\n")
        self.datafile.flush()

    def write_proc_header(self, step_value, unit_step_value):
        if I.CONFIG_MEASURE_R1_CURRENT:
            C1, C2, U12 = "I1", "deltaI1", "A"
        else:
            C1, C2, U12 = "U1", "deltaU1", "V"
        P = [step_value,
             C1, C2, "Phase1", "deltaPhase1",
             "U2", "deltaU2", "Phase2", "deltaPhase2",
             "U3", "deltaU3", "Phase3", "deltaPhase3",
             "U4", "deltaU4", "Phase4", "deltaPhase4",
             "H", "deltaH", "Hall", "deltaHall",
             "T", "deltaT", "T7", "deltaT7", "T8", "deltaT8",
             "RK", "deltaRK"]
        U = [unit_step_value,
             U12, U12, "Degrees", "Degrees",
             "V", "V", "Degrees", "Degrees",
             "V", "V", "Degrees", "Degrees",
             "V", "V", "Degrees", "Degrees",
             "T", "T", "T", "T",
             "K", "K", "Ohm", "Ohm", "Ohm", "Ohm",
             "Ohm", "Ohm"]
        self.procfile.write("\t".join(P) + "\n")
        self.procfile.write("\t".join(U) + "\n")
        self.procfile.flush()

    def write_proc(self, step, R1, deltaR1, Phase1, deltaPhase1, R2, deltaR2, Phase2, deltaPhase2, R3, deltaR3, Phase3,
                   deltaPhase3, R4, deltaR4, Phase4, deltaPhase4, H, deltaH, Hall, deltaHall, T, deltaT, T7, deltaT7,
                   T8, deltaT8, RK, deltaRK):
        D = [step, R1, deltaR1, Phase1, deltaPhase1, R2, deltaR2, Phase2, deltaPhase2, R3, deltaR3, Phase3, deltaPhase3,
             R4, deltaR4, Phase4, deltaPhase4, H, deltaH, Hall, deltaHall, T, deltaT, T7, deltaT7, T8, deltaT8, RK,
             deltaRK]
        self.procfile.write("\t".join([str(x) for x in D]) + "\n")
        self.procfile.flush()

    def run(self):
        logging.info("MEASURER: Measurements started")

        self.init_files(self.sample, self.name)
        if self.EXPERIMENT == "cooldown":
            self.write_header_cooldown()
        else:
            self.write_header()

        r1_output_overload_in_row = 0
        r2_output_overload_in_row = 0
        r3_output_overload_in_row = 0
        r4_output_overload_in_row = 0

        while not self.stopped:
            TIME = time.perf_counter() - self.START_TIME

            try:
                if I.CONFIG_MEASURE_R1:
                    u1, phase1 = I.get_amplitude_and_theta(I.R1)
                    if len(self.R1) % 100 == 0:
                        status = I.get_status(I.R1)
                        if status:
                            logging.warning(f"R1 status = {status}")
                            self.R1annotations.append((TIME, u1, status))

                        if "OUT" in status:
                            r1_output_overload_in_row += 1
                            if r1_output_overload_in_row == 3:
                                logging.info(f"R1: OVERLOAD THREE TIMES IN A RO  W (AUTORANGE={self.AUTORANGE})")
                                if self.AUTORANGE:
                                    I.range_up(I.R1)
                        else:
                            r1_output_overload_in_row = 0
                else:
                    u1, phase1 = 0, 0

                if I.CONFIG_MEASURE_R2:
                    u2, phase2 = I.get_amplitude_and_theta(I.R2)
                    if len(self.R2) % 100 == 0:
                        status = I.get_status(I.R2)
                        if status:
                            logging.warning(f"R2 status = {status}")
                            self.R2annotations.append((TIME, u2, status))

                        if "OUT" in status:
                            r2_output_overload_in_row += 1
                            if r2_output_overload_in_row == 3:
                                logging.info(f"R2: OVERLOAD THREE TIMES IN A ROW (AUTORANGE={self.AUTORANGE})")
                                if self.AUTORANGE:
                                    I.range_up(I.R2)
                        else:
                            r2_output_overload_in_row = 0
                else:
                    u2, phase2 = 0, 0

                if I.CONFIG_MEASURE_R3:
                    u3, phase3 = I.get_amplitude_and_theta(I.R3)
                    if len(self.R3) % 100 == 0:
                        status = I.get_status(I.R3)
                        if status:
                            logging.warning(f"R3 status = {status}")
                            self.R3annotations.append((TIME, u3, status))

                        if "OUT" in status:
                            r3_output_overload_in_row += 1
                            if r3_output_overload_in_row == 3:
                                logging.info(f"R3: OVERLOAD THREE TIMES IN A ROW (AUTORANGE={self.AUTORANGE})")
                                if self.AUTORANGE:
                                    I.range_up(I.R3)
                        else:
                            r3_output_overload_in_row = 0
                else:
                    u3, phase3 = 0, 0

                if I.CONFIG_MEASURE_R4:
                    u4, phase4 = I.get_amplitude_and_theta(I.R4)
                    if len(self.R4) % 100 == 0:
                        status = I.get_status(I.R4)
                        if status:
                            logging.warning(f"R4 status = {status}")
                            self.R4annotations.append((TIME, u4, status))

                        if "OUT" in status:
                            r4_output_overload_in_row += 1
                            if r4_output_overload_in_row == 3:
                                logging.info(f"R4: OVERLOAD THREE TIMES IN A ROW (AUTORANGE={self.AUTORANGE})")
                                if self.AUTORANGE:
                                    I.range_up(I.R4)
                        else:
                            r4_output_overload_in_row = 0
                else:
                    u4, phase4 = 0, 0

                if I.CONFIG_MEASURE_FIELD:
                    h = I.get_current_field()
                else:
                    h = 0

                if I.CONFIG_MEASURE_HALL:
                    with DEVICELOCK:
                        hall = I.T.query_ascii_values("RDGR? 8")[0]
                    # with DEVICELOCK:
                    #     hall, = I.Hall.query_ascii_values("DATA?")
                else:
                    hall = 0
                if I.CONFIG_MEASURE_LakeShore_T1:
                    with DEVICELOCK:
                        tr1 = I.LT1.query_ascii_values("KRDG? A")[0]
                        tr2 = 0
                if I.CONFIG_MEASURE_LakeShore_T2:
                    with DEVICELOCK:
                        tr1 = I.LT2.query_ascii_values("KRDG? A")[0]
                        tr2 = I.LT2.query_ascii_values("KRDG? B")[0]

                if I.CONFIG_MEASURE_Keithley_R1:
                    with DEVICELOCK:
                        r_sample = I.Rsample.query_ascii_values(':DATA?')[0]
                else:
                    r_sample = 0
                if I.CONFIG_MEASURE_Lockin:
                    with DEVICELOCK:
                        data = I.Lockin.query_ascii_values('SNAP? 1,2,3,4')
                        ux=data[0]
                        uy=data[1]
                        ur=data[2]
                        tetta=data[3]
                if I.CONFIG_MEASURE_RK:
                    with DEVICELOCK:
                        rk_v, rk_i, rk_r, rk_g1, rk_g2 = I.RK.query_ascii_values(":READ?")
                        rk = rk_r
                else:
                    rk = 0

                t = t7 = t8 = None

                if FACILITY == Facility.BLUEFORS:
                    tc_channel = I.get_tc_channel()
                elif FACILITY == Facility.CFMS:
                    tc_channel = 6
                elif FACILITY == FACILITY.STUDENT_INSERT:
                    tc_channel = 'A'

                if tc_channel == 6:
                    t = I.get_temperature()
                elif tc_channel == 7:
                    with DEVICELOCK:
                        t7 = I.T.query_ascii_values("RDGR? 7")[0]
                elif tc_channel == 8:
                    with DEVICELOCK:
                        t8 = I.T.query_ascii_values("RDGR? 8")[0]

                if self.EXPERIMENT == "cooldown":
                    t1 = t2 = t3 = t5 = t6 = t7 = t8 = None
                    with DEVICELOCK:
                        channel = int(I.T.query("SCAN?").strip().split(",")[0])
                        if channel == 1:
                            t1 = float(I.T.query("RDGK? 1").strip())
                        elif channel == 2:
                            t2 = float(I.T.query("RDGK? 2").strip())
                        elif channel == 3:
                            t3 = float(I.T.query("RDGK? 3").strip())
                        elif channel == 5:
                            t5 = float(I.T.query("RDGK? 5").strip())
                        elif channel == 6:
                            t6 = float(I.T.query("RDGK? 6").strip())
                        elif channel == 7:
                            t7 = float(I.T.query("RDGR? 7").strip())
                        elif channel == 8:
                            t8 = float(I.T.query("RDGR? 8").strip())
                        else:
                            logging.info("UNKNOWN CHANNEL!")

                    self.T1.append(t1)
                    self.T2.append(t2)
                    self.T3.append(t3)
                    self.T5.append(t5)
                    self.T6.append(t6)
                    # self.T7.append(t7)
                    # self.T8.append(t8)

            except Exception as exc:
                logging.info("MEASURER: Cannot obtain point!")
                logging.exception(exc)
            else:
                self.R1.append(u1)
                self.PHASE1.append(phase1)
                self.R2.append(u2)
                self.PHASE2.append(phase2)
                self.R3.append(u3)
                self.PHASE3.append(phase3)
                self.R4.append(u4)
                self.PHASE4.append(phase4)
                self.H.append(h)
                self.HALL.append(hall)
                self.T.append(t)
                self.T7.append(t7)
                self.T8.append(t8)
                self.RK.append(rk)
                self.TIME.append(TIME)
                self.Tsample2.append(tr2)
                self.Tsample1.append(tr1)
                self.R_Sample.append(r_sample)
                self.Ux.append(ux)
                self.Uy.append(uy)
                self.Ur.append(ur)
                self.Tetta.append(tetta)

                if self.EXPERIMENT == "cooldown":
                    self.write_data_cooldown(TIME, u1, phase1, u2, phase2, u3, phase3, u4, phase4, h, hall, t1, t2, t3,
                                             t5, t6, t7, t8)
                else:
                    self.write_data(TIME, u1, phase1, u2, phase2, u3, phase3, u4, phase4, h, hall, t, t7, t8, rk, tr1,
                                    tr2, r_sample, ux, uy, ur, tetta)

            if self.EXPERIMENT == "step":
                if self.STEP_LASTTIME is None or (
                        TIME - self.STEP_LASTTIME >= self.STEP_MEASURE_TIME + self.STEP_RELAX_TIME):
                    if self.STEP_FIRSTPOINT is not None:
                        # It's not the first point
                        # We have to remove None from list to calculate mean value
                        mean_dev = lambda arr: (
                            np.mean([x for x in arr if x is not None]), np.std([x for x in arr if x is not None]))

                        R1M, R1D = mean_dev(self.R1[self.STEP_FIRSTPOINT:])
                        P1M, P1D = mean_dev(self.PHASE1[self.STEP_FIRSTPOINT:])
                        R2M, R2D = mean_dev(self.R2[self.STEP_FIRSTPOINT:])
                        P2M, P2D = mean_dev(self.PHASE2[self.STEP_FIRSTPOINT:])
                        R3M, R3D = mean_dev(self.R3[self.STEP_FIRSTPOINT:])
                        P3M, P3D = mean_dev(self.PHASE3[self.STEP_FIRSTPOINT:])
                        R4M, R4D = mean_dev(self.R4[self.STEP_FIRSTPOINT:])
                        P4M, P4D = mean_dev(self.PHASE4[self.STEP_FIRSTPOINT:])
                        HM, HD = mean_dev(self.H[self.STEP_FIRSTPOINT:])
                        HallM, HallD = mean_dev(self.HALL[self.STEP_FIRSTPOINT:])
                        TM, TD = mean_dev(self.T[self.STEP_FIRSTPOINT:])
                        T7M, T7D = mean_dev(self.T7[self.STEP_FIRSTPOINT:])
                        T8M, T8D = mean_dev(self.T8[self.STEP_FIRSTPOINT:])
                        RKM, RKD = mean_dev(self.RK[self.STEP_FIRSTPOINT:])

                        self.write_proc(self.STEP_LIST[0],
                                        R1M, R1D, P1M, P1D,
                                        R2M, R2D, P2M, P2D,
                                        R3M, R3D, P3M, P3D,
                                        R4M, R4D, P4M, P4D,
                                        HM, HD, HallM, HallD,
                                        TM, TD, T7M, T7D, T8M, T8D,
                                        RKM, RKD)

                        self.STEP_LIST.pop(0)

                    if len(self.STEP_LIST) == 0:
                        break

                    if self.STEP_VALUE == "VG":
                        I.set_gate_voltage(self.STEP_LIST[0])
                    elif self.STEP_VALUE == "AMP-R1":
                        I.set_amplitude(I.R1, self.STEP_LIST[0])
                    elif self.STEP_VALUE == "AMP-ALL":
                        if I.CONFIG_MEASURE_R1:
                            I.set_amplitude(I.R1, self.STEP_LIST[0])
                        if I.CONFIG_MEASURE_R2:
                            I.set_amplitude(I.R2, self.STEP_LIST[0])
                        if I.CONFIG_MEASURE_R3:
                            I.set_amplitude(I.R3, self.STEP_LIST[0])
                        if I.CONFIG_MEASURE_R4:
                            I.set_amplitude(I.R4, self.STEP_LIST[0])
                    elif self.STEP_VALUE == "FREQ":
                        I.set_frequency(I.R1, self.STEP_LIST[0])
                    elif self.STEP_VALUE == "H":
                        I.set_target_field(self.STEP_LIST[0])
                    elif self.STEP_VALUE == "HEATER":
                        I.tc_heater(self.STEP_LIST[0])

                    if self.STEP_LASTTIME is None:
                        self.write_proc_header(self.STEP_VALUE, "")

                    self.STEP_LASTTIME = TIME
                    self.STEP_FIRSTPOINT = None

                elif TIME - self.STEP_LASTTIME >= self.STEP_RELAX_TIME:
                    if self.STEP_FIRSTPOINT is None:
                        self.STEP_FIRSTPOINT = len(self.TIME) - 1

                else:
                    # This point is not needed
                    self.TIME.pop()
                    self.R1.pop()
                    self.PHASE1.pop()
                    self.R2.pop()
                    self.PHASE2.pop()
                    self.R3.pop()
                    self.PHASE3.pop()
                    self.R4.pop()
                    self.PHASE4.pop()
                    self.H.pop()
                    self.HALL.pop()
                    self.T.pop()
                    self.T7.pop()
                    self.T8.pop()
                    self.RK.pop()

        logging.info("MEASURER: Measurements stopped")
        self.stopped = True

    def requestInterruption(self):
        self.stopped = True


class ExceptionSyntaxError(Exception):
    pass


class Program(threading.Thread):
    def __init__(self):
        super().__init__()

        self.stopped = False
        self.commands = program_widget.toPlainText().split("\n")

    def run_commands(self, dryrun=True) -> Optional[float]:
        global MEASURER_OBJECT
        CONFIG_STEP_RELAX = None
        CONFIG_STEP_MEASURE = None
        CONFIG_AUTORANGE = None

        total_time_in_seconds = 0
        current_field = None
        current_temperature = None

        log_info = "\n" + "*" * 25 + "\n" + "\n".join(self.commands) + "\n" + "*" * 25
        logging.info(log_info)

        try:
            for lineno, cmd in enumerate(self.commands, start=1):
                if self.stopped:
                    break

                if not cmd:
                    continue

                command, *args = cmd.split(" ")

                # Remove empty commands
                args = [A.strip() for A in args if A.strip()]

                logging.info("{:02d}: Processing command {}({})".format(lineno, command, ",".join(args)))

                if command == "config":
                    try:
                        param_name = args[0]
                        param_value = args[1]
                    except IndexError:
                        raise ExceptionSyntaxError(
                            "config [step-relax,step-measure,current-field,current-temperature] <value>")

                    if param_name == "step-relax":
                        try:
                            CONFIG_STEP_RELAX = float(param_value)
                            logging.info(f"CONFIG_STEP_RELAX set to {CONFIG_STEP_RELAX}")
                        except ValueError:
                            raise ExceptionSyntaxError
                    elif param_name == "step-measure":
                        try:
                            CONFIG_STEP_MEASURE = float(param_value)
                            logging.info(f"CONFIG_STEP_MEASURE set to {CONFIG_STEP_MEASURE}")
                        except ValueError:
                            raise ExceptionSyntaxError
                    elif param_name == "current-field":
                        try:
                            current_field = float(param_value)
                            logging.info(f"Setting current field to {current_field} T")
                        except ValueError:
                            raise ExceptionSyntaxError
                    elif param_name == "current-temperature":
                        try:
                            current_temperature = float(param_value)
                            logging.info(f"Setting current temperature to {current_temperature} K")
                        except ValueError:
                            raise ExceptionSyntaxError
                    elif param_name == "autorange":
                        if param_value.lower() in ["on", "1"]:
                            CONFIG_AUTORANGE = True
                        elif param_value.lower() in ["off", "0"]:
                            CONFIG_AUTORANGE = False
                        else:
                            raise ExceptionSyntaxError(f"Unknown parameter value for AUTORANGE!")
                    else:
                        raise ExceptionSyntaxError("Unknown parameter name!")

                elif command == "start-simple":
                    try:
                        name = args[0]
                    except IndexError:
                        raise ExceptionSyntaxError("start-simple <EXPERIMENT_NAME>")

                    if not dryrun:

                        # if FACILITY == Facility.BLUEFORS:
                        #     if I.CONFIG_MEASURE_PT_FLANGE:
                        #         I.select_channel(2, 0)
                        #     else:
                        #         I.select_channel(6, 0)

                        logging.info("Creating Measurer...")
                        MEASURER_OBJECT = Measurer()
                        MEASURER_OBJECT.sample = SAMPLE
                        MEASURER_OBJECT.name = name
                        MEASURER_OBJECT.EXPERIMENT = "simple"
                        if CONFIG_AUTORANGE is not None:
                            MEASURER_OBJECT.AUTORANGE = CONFIG_AUTORANGE

                        logging.info("Starting Measurer...")
                        MEASURER_OBJECT.start()

                elif command == "start-cooldown":
                    try:
                        name = args[0]
                    except IndexError:
                        raise ExceptionSyntaxError("start-cooldown <EXPERIMENT_NAME>")

                    if not dryrun:
                        if FACILITY == Facility.BLUEFORS:
                            I.select_channel(1, 1)

                        logging.info("Creating Measurer...")
                        MEASURER_OBJECT = Measurer()
                        MEASURER_OBJECT.sample = SAMPLE
                        MEASURER_OBJECT.name = name
                        MEASURER_OBJECT.EXPERIMENT = "cooldown"
                        if CONFIG_AUTORANGE is not None:
                            MEASURER_OBJECT.AUTORANGE = CONFIG_AUTORANGE

                        logging.info("Starting Measurer...")
                        MEASURER_OBJECT.start()

                elif command == "start-step":
                    try:
                        name = args[0]
                        step = args[1]
                        value_from, value_to = [float(x) for x in args[2].split("..")]
                        numpoints, zigzag = [int(x) for x in args[3].split("*")]
                    except (IndexError, ValueError):
                        raise ExceptionSyntaxError("start-step <NAME> <STEP> <FROM>..<TO> <POINTS>*<ZIGZAG>")

                    if CONFIG_STEP_RELAX is None:
                        raise ExceptionSyntaxError("CONFIG_STEP_RELAX not set!")

                    if CONFIG_STEP_MEASURE is None:
                        raise ExceptionSyntaxError("CONFIG_STEP_MEASURE not set!")

                    STEP_PARAM_AVAILABLE = ["AMP-R1", "AMP-ALL", "FREQ", "VG", "H", "HEATER"]
                    if step.upper() not in STEP_PARAM_AVAILABLE:
                        raise ExceptionSyntaxError(
                            "Unknown step parameter! Must be from list {}".format(STEP_PARAM_AVAILABLE))

                    steplist = []
                    for i in range(zigzag):
                        if i % 2 == 0:
                            steplist.extend(list(np.linspace(value_from, value_to, numpoints)))
                        else:
                            steplist.extend(reversed(list(np.linspace(value_from, value_to, numpoints))))

                    estimated_time_in_seconds = len(steplist) * (CONFIG_STEP_MEASURE + CONFIG_STEP_RELAX)
                    logging.info("Step experiment will take {:.1f} minutes".format(estimated_time_in_seconds / 60))

                    total_time_in_seconds += estimated_time_in_seconds

                    if not dryrun:
                        logging.info("Creating Measurer...")
                        MEASURER_OBJECT = Measurer()

                        MEASURER_OBJECT.sample = SAMPLE
                        MEASURER_OBJECT.name = name

                        MEASURER_OBJECT.EXPERIMENT = "step"
                        MEASURER_OBJECT.STEP_VALUE = step.upper()
                        MEASURER_OBJECT.STEP_RELAX_TIME = CONFIG_STEP_RELAX
                        MEASURER_OBJECT.STEP_MEASURE_TIME = CONFIG_STEP_MEASURE
                        MEASURER_OBJECT.STEP_LIST = steplist
                        if CONFIG_AUTORANGE is not None:
                            MEASURER_OBJECT.AUTORANGE = CONFIG_AUTORANGE

                        logging.info("Starting Measurer...")
                        MEASURER_OBJECT.start()

                elif command == "start-didv":
                    try:
                        name = args[0]
                        value_from, value_to = [float(x) for x in args[1].split("..")]
                        numpoints = int(args[2])
                        with_str, delta_str = args[3], args[4]
                        assert with_str == "with"
                        assert delta_str == "delta"
                        delta = float(args[5])
                    except (IndexError, ValueError):
                        raise ExceptionSyntaxError("start-didv <NAME> <FROM>..<TO> <POINTS> with delta <DELTA>")

                    if not dryrun:
                        logging.info("Creating DiDvMeasurer...")
                        MEASURER_OBJECT = DiDvMeasurer()

                        MEASURER_OBJECT.sample = SAMPLE
                        MEASURER_OBJECT.name = name

                        MEASURER_OBJECT.current_start = value_from
                        MEASURER_OBJECT.current_finish = value_to
                        MEASURER_OBJECT.numsteps = numpoints
                        MEASURER_OBJECT.current_delta = delta
                        if CONFIG_AUTORANGE is not None:
                            MEASURER_OBJECT.AUTORANGE = CONFIG_AUTORANGE

                        logging.info("Starting DiDvMeasurer...")
                        MEASURER_OBJECT.start()

                elif command == "tc-current":
                    try:
                        tow = args[0].strip().lower()
                        assert tow in ["up", "down"]
                    except (IndexError, ValueError, AssertionError):
                        raise ExceptionSyntaxError("tc-current [up|down]")

                    if tow == "down":
                        if not dryrun:
                            I.tc_current_down()
                    elif tow == "up":
                        if not dryrun:
                            I.tc_current_up()
                    else:
                        raise ExceptionSyntaxError("Impossible situation!")
                elif command == "set-rng":
                    try:
                        tow = args[1]
                        channel = int(args[0])
                    except (IndexError, ValueError):
                        raise ExceptionSyntaxError("set-rng <channel> <direction>")

                    if not dryrun:
                        if tow == "DOWN":
                            mode, excitation, rng, autorange, cs = I.T.query_ascii_values(f"RDGRNG? {channel}")
                            if excitation > 1:
                                I.T.write(f"RDGRNG {channel},{mode},{excitation},{rng - 1},{autorange},{cs}")
                                logging.info(
                                    f"Setting TC range of channel {channel} to {I.TC_CURRENT_RANGE_LABELS[rng - 1]}")
                        elif tow == "UP":
                            mode, excitation, rng, autorange, cs = I.T.query_ascii_values(f"RDGRNG? {channel}")
                            if excitation < 22:
                                I.T.write(f"RDGRNG {channel},{mode},{excitation},{rng + 1},{autorange},{cs}")
                                logging.info(
                                    f"Setting TC range of channel {channel} to {I.TC_CURRENT_RANGE_LABELS[rng + 1]}")

                elif command == "stop":
                    if not dryrun:
                        if MEASURER_OBJECT is not None:
                            logging.info("Waiting for MEASURER to stop in up to 10 seconds...")
                            MEASURER_OBJECT.requestInterruption()
                            MEASURER_OBJECT.join(10)
                            if MEASURER_OBJECT.is_alive():
                                logging.error("Error on waiting for MEASURER_OBJECT to stop")
                            del MEASURER_OBJECT
                            MEASURER_OBJECT = None
                        else:
                            logging.error("Experiment not started!")

                elif command == "wait":
                    try:
                        seconds, units = args
                        seconds = float(seconds)
                        if units in ("s", "sec", "seconds"):
                            seconds = seconds
                        elif units in ("m", "min", "minutes", "minute"):
                            seconds *= 60
                        elif units in ("h", "hours", "hour"):
                            seconds *= 3600
                        else:
                            raise AssertionError
                    except (ValueError, IndexError, AssertionError):
                        raise ExceptionSyntaxError(
                            "Syntax error! wait <time> [s,sec,seconds,m,min,minute,minutes,h,hour,hours]")

                    logging.info(f"WAIT: Waiting for {seconds} seconds")

                    total_time_in_seconds += seconds
                    if not dryrun:
                        while seconds > 0 and not self.stopped:
                            time.sleep(5)
                            seconds -= 5

                    logging.info("WAIT: Pause finished")

                elif command == "wait-for-field":
                    logging.info("WAIT: Waiting for field stabilizing")
                    if not dryrun:
                        while I.get_magnet_ramping() and not self.stopped:
                            time.sleep(5)
                    logging.info("WAIT: Field stabilized")

                elif command == "wait-for-temperature":
                    logging.info("WAIT: Waiting for temperature stabilizing")
                    if not dryrun:
                        while I.get_temperature_ramping() and not self.stopped:
                            time.sleep(5)
                    logging.info("WAIT: Temperature stabilized")

                elif command == "wait-for-program":
                    logging.info("WAIT: Waiting for program finishing")
                    if not dryrun:
                        if MEASURER_OBJECT is not None:
                            while not MEASURER_OBJECT.stopped and not self.stopped:
                                time.sleep(5)
                    logging.info("WAIT: Program finished")

                elif command in ["set-gate-voltage", "set-gate-current"]:
                    try:
                        value, units = float(args[0]), args[1].lower()
                    except (ValueError, IndexError):
                        raise ExceptionSyntaxError(
                            "set-gate-voltage <voltage> [V,mV] | set-gate-current <current] [A,mA]")
                    if units in ["v", "a"]:
                        pass
                    elif units in ["mv", "ma"]:
                        value *= 1e-3
                    else:
                        raise ExceptionSyntaxError(
                            "set-gate-voltage <voltage> [V,mV] | set-gate-current <current] [A,mA]")

                    if command == "set-gate-voltage":
                        logging.info(f"Setting gate voltage to {value} V")
                        if not dryrun:
                            I.set_gate_voltage(value)
                    elif command == "set-gate-current":
                        logging.info(f"Setting gate current to {value} A")
                        if not dryrun:
                            I.set_gate_current(value)
                elif command == "set-gate-state":
                    try:
                        state = int(args[0])
                    except (ValueError, IndexError):
                        raise ExceptionSyntaxError("set-gate-state {0|1}")
                    logging.info(f"Setting gate state to {state}")
                    if not dryrun:
                        I.set_gate_state(state)

                elif command == "set-target-field":
                    try:
                        field, field_unit, wrd_with, wrd_rate, rate, rate_unit = args
                        field = float(field)
                        if field_unit == "T":
                            field = field
                        elif field_unit == "Oe":
                            field = field * 0.0001
                        else:
                            raise AssertionError

                        assert wrd_with == "with"
                        assert wrd_rate == "rate"

                        rate = float(rate)
                        if rate_unit == "T/min":
                            rate = rate
                        elif rate_unit == "Oe/min":
                            rate = rate * 0.0001
                        else:
                            raise AssertionError

                    except (ValueError, IndexError, AssertionError):
                        raise ExceptionSyntaxError("set-target-field <field> [T,Oe] with rate <rate> [T/min,Oe/min]")
                    logging.info("Setting target field to {} T with rate {} T/min".format(field, rate))

                    if current_field is not None:
                        delay = abs(field - current_field) / rate * 60.0
                        logging.info(
                            f"It will take {int(delay / 3600):02d}:{int(delay / 60 % 60):02d}:{int(delay % 60):02d} seconds")
                        total_time_in_seconds += delay
                        current_field = field
                    else:
                        raise ExceptionSyntaxError("CURRENT_FIELD NOT SET!")

                    if not dryrun:
                        I.set_target_field(field, rate)

                elif command == "set-target-temperature":
                    try:
                        temp, temp_unit, wrd_with, wrd_rate, rate, rate_unit = args

                        temp = float(temp)
                        if temp_unit == "K":
                            temp = temp
                        elif temp_unit == "mK":
                            temp = temp * 0.001
                        else:
                            raise AssertionError

                        assert wrd_with == "with"
                        assert wrd_rate == "rate"

                        rate = float(rate)
                        if rate_unit == "K/min":
                            rate = rate * 1000
                        elif rate_unit == "mK/min":
                            rate = rate
                        else:
                            raise AssertionError

                    except (ValueError, IndexError, AssertionError):
                        raise ExceptionSyntaxError(
                            "Syntax error! set-target-temperature <temp> [K,mK] with rate <rate> K/min")
                    logging.info(f"Setting target temperature to {temp} K with rate {rate} mK/min")

                    if current_temperature is not None:
                        delay = abs(temp - current_temperature) / (rate / 1000) * 60.0
                        logging.info(
                            f"It will take {int(delay / 3600):02d}:{int(delay / 60 % 60):02d}:{int(delay % 60):02d} seconds")
                        total_time_in_seconds += delay
                        current_temperature = temp
                    else:
                        raise ExceptionSyntaxError("CURRENT_TEMPERATURE NOT SET!")

                    if not dryrun:
                        # I.set_temperature_ramp(True, rate)
                        # rate in mK/min
                        I.set_target_temperature(temp, rate)

                elif command == "set-amplitude":
                    try:
                        amp = float(args[0])
                    except (ValueError, IndexError):
                        raise ExceptionSyntaxError("Cannot determine amplitude!")
                    logging.info("Setting amplitude to {}".format(amp))
                    if not dryrun:
                        I.set_amplitude(I.R1, amp)

                elif command == "set-frequency":
                    try:
                        freq = float(args[0])
                    except (ValueError, IndexError):
                        raise ExceptionSyntaxError("Cannot determine frequency!")
                    logging.info("Setting frequency to {}".format(freq))
                    if not dryrun:
                        I.set_frequency(I.R1, freq)

                elif command == "set-offset-and-expand":
                    try:
                        lockin_number, onoff, mult = args[0].strip().lower(), args[1].strip().lower(), args[
                            2].strip().lower()
                        assert lockin_number in ["r1", "r2", "r3", "r4"]
                        assert onoff in ["on", "off"]
                        assert mult in ["1x", "10x", "100x"]
                    except (ValueError, IndexError, AssertionError):
                        raise ExceptionSyntaxError(
                            "Syntax error! set-offset-and-expand <R1|R2|R3|R4> <on|off> <1x|10x|100x>")

                    sr830 = {"r1": I.R1, "r2": I.R2, "r3": I.R3, "r4": I.R4}[lockin_number]

                    if onoff == "on":
                        logging.info(f"Enabling offset for {lockin_number.upper()} with expand {mult}")
                        if not dryrun:
                            offset = I.set_offset_expand_on(sr830, mult)
                            logging.info(f"Offset for {lockin_number.upper()}: {offset}%")
                    elif onoff == "off":
                        logging.info(f"Disabling offset and expand for {lockin_number.upper()}")
                        if not dryrun:
                            I.set_offset_expand_off(sr830)
                    else:
                        raise ExceptionSyntaxError("IMPOSSIBLE SITUATION!")

                elif command == "tc-channel":
                    try:
                        channel = int(args[0])
                    except (ValueError, IndexError):
                        raise ExceptionSyntaxError("Cannot determine channel number!")
                    logging.info("Setting channel to {}".format(channel))
                    if not dryrun:
                        I.select_channel(channel, 0)

                else:
                    raise ExceptionSyntaxError("Unknown command!")

        except ExceptionSyntaxError as exc:
            logging.exception(exc)
            return None
        except Exception as exc:
            logging.warning("Exception in program thread!")
            logging.exception(exc)
            return None

        return total_time_in_seconds

    def check(self):
        self.commands = program_widget.toPlainText().split("\n")
        estimated_time = self.run_commands(dryrun=True)
        if estimated_time is not None:
            logging.info(f"Estimated time is {estimated_time / 60 / 60:.1f} hours ({estimated_time / 60:.1f} minutes)")
            finish_time = datetime.datetime.now() + datetime.timedelta(seconds=estimated_time)
            logging.info("Experiment will be finished at {:%H:%M}".format(finish_time))
        return estimated_time is not None

    def run(self):
        self.run_commands(dryrun=False)
        self.stopped = True

    def requestInterruption(self):
        self.stopped = True


class MonitoringThread(threading.Thread):
    def __init__(self):
        super().__init__()

        self.stopped = False
        self.server = None

    def status(self):
        global MEASURER_OBJECT

        D = {}
        if MEASURER_OBJECT is None:
            D["message"] = "Experiment stopped"
        else:
            D["message"] = "Experiment running"
            D["R1"] = MEASURER_OBJECT.R1[-1]
            D["R2"] = MEASURER_OBJECT.R2[-1]
            D["R3"] = MEASURER_OBJECT.R3[-1]
            D["R4"] = MEASURER_OBJECT.R4[-1]
            D["PHASE1"] = MEASURER_OBJECT.PHASE1[-1]
            D["PHASE2"] = MEASURER_OBJECT.PHASE2[-1]
            D["PHASE3"] = MEASURER_OBJECT.PHASE3[-1]
            D["PHASE4"] = MEASURER_OBJECT.PHASE4[-1]
            D["H"] = MEASURER_OBJECT.H[-1]
            D["HALL"] = MEASURER_OBJECT.HALL[-1]
            D["T"] = MEASURER_OBJECT.T[-1]

            if MEASURER_OBJECT.EXPERIMENT == "cooldown":
                D["T1"] = MEASURER_OBJECT.T1[-1]
                D["T2"] = MEASURER_OBJECT.T2[-1]
                D["T3"] = MEASURER_OBJECT.T3[-1]
                D["T5"] = MEASURER_OBJECT.T5[-1]
                D["T6"] = MEASURER_OBJECT.T6[-1]

        return D

    def run(self):
        while not self.stopped:
            logging.info("Starting monitoring server")
            try:
                with xmlrpc.server.SimpleXMLRPCServer(("localhost", 13000), allow_none=True,
                                                      logRequests=False) as self.server:
                    self.server.register_function(self.status, "status")
                    self.server.serve_forever()
            except Exception as exc:
                logging.warning("Exception in monitoring thread!")
                logging.exception(exc)

    def requestInterruption(self):
        self.stopped = True
        self.server.shutdown()


# Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys

    logging.info("Application started")

    I = Instruments()

    # MONITORING_OBJECT = MonitoringThread()
    # MONITORING_OBJECT.start()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec()

    # if MONITORING_OBJECT is not None:
    #     logging.info("Stopping monitoring")
    #     MONITORING_OBJECT.requestInterruption()
    #     MONITORING_OBJECT.join(5)
    #     if MONITORING_OBJECT.is_alive():
    #         logging.error("Error stopping monitoring thread")
    #     logging.info("MONITORING_OBJECT finished")

    if PROGRAM_OBJECT is not None:
        logging.info("Stopping program thread")
        PROGRAM_OBJECT.requestInterruption()
        PROGRAM_OBJECT.join(5)
        if PROGRAM_OBJECT.is_alive():
            logging.error("Error stopping program thread")
        logging.info("PROGRAM_OBJECT finished")

    if MEASURER_OBJECT is not None:
        logging.info("Waiting for MEASURER to stop in up to 10 seconds...")
        MEASURER_OBJECT.requestInterruption()
        MEASURER_OBJECT.join(10)
        if MEASURER_OBJECT.is_alive():
            logging.error("Error stopping measurer thread")
        logging.info("MEASURER_OBJECT finished")

    logging.info("Application finished")
