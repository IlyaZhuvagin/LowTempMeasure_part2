from typing import Tuple, List, Dict, Union, Optional
import pyvisa
import time
import pyvisa.constants
import pyvisa.resources as visa_res
import instruments.keithley6221 as keithley6221
import logging
import enum
import matplotlib.pyplot as plt
import pyvisa
from datetime import datetime


class UNITS(enum.Enum):
    Volts = "V"
    Ohms = "OHMS"
    Watts = "W"
    Siemens = "SIEM"

K1 = keithley6221.Keithley6221(address="GPIB0::13::INSTR", rm=pyvisa.ResourceManager())

time.sleep(1)
#K1._device.write('SYST:COMM:SER:SEND "VOLT:NPLC 1"')
#K1._device.write('SYST:COMM:SER:SEND "VOLT:NPLC?"')
#cc=K1._device.query('SYST:COMM:SER:ENT?').strip()
#print('Result:cc=',cc)

print('Measuring by Delta mode:')
print('R(t)')
###########################################################
I=220E-9
tmax=60
###########################################################

Delay=0.002 #s

K1.RunDeltaMeasurements(UNITS.Ohms,I,Delay,"INF",1)
time.sleep(1)

K1._device.write('SYST:COMM:SER:SEND "VOLT:NPLC 1"')

#cc=K1._device.query('SYST:COMM:SER:ENT?')
#time.sleep(1)


file = open("Cooling_curve.txt", "w")
#file = open("Middle_resistance.txt", "w")
t=0
t_start = time.perf_counter()
while t < tmax:
      R = K1.GetData()
      t = time.perf_counter() - t_start
      #print(t)
      file.write('%s' % t)
      file.write(' %s\n' % R)


K1._device.write("SOUR:SWE:ABOR")
file.close()
#bb=K1._device.write('SYST:COMM:SER:SEND "VOLT:NPLC?"')
#print(bb)
#cc=K1._device.query('SYST:COMM:SER:ENT?')
#print('Result:cc=',cc)

print("It's done!")