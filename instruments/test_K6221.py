from typing import Tuple, List, Dict, Union, Optional
import pyvisa
import time
import pyvisa.constants
import pyvisa.resources as visa_res
import instruments.keithley6221 as keithley6221
import logging
import enum
import numpy as np
import matplotlib.pyplot as plt
import pyvisa
from datetime import datetime


class UNITS(enum.Enum):
    Volts = "V"
    Ohms = "OHMS"
    Watts = "W"
    Siemens = "SIEM"

K1 = keithley6221.Keithley6221(address="GPIB0::13::INSTR", rm=pyvisa.ResourceManager())

print('Measuring by Delta mode:')
print('V(I)')

I=np.arange(2e-9,47e-9,2e-9)
#I=np.arange(10e-9,110e-9,10e-9)
Delay=0.002 #s
file = open("Thermometer.txt", "w")
#file = open("Heater.txt", "w")

K1._device.write('SYST:COMM:SER:SEND "VOLT:NPLC 1"')
for x in I:
    K1.RunDeltaMeasurements(UNITS.Volts,x,Delay,"INF",1,)
    time.sleep(2)
    Vmid=K1.GetData();

    i = 1
    t_start = time.perf_counter()
    t_stop = time.perf_counter()
    while (t_stop - t_start) < 5:
        Vmid = (Vmid * i + K1.GetData()) / (i + 1)
        i = i + 1;
        t_stop = time.perf_counter()

    K1._device.write("SOUR:SWE:ABOR")
    time.sleep(1)
    print(x,'A')
    file.write('%s' % x)
    file.write(' %s\n' % Vmid)

file.close()
print("It's done!")
