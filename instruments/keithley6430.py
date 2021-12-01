import pyvisa
import pyvisa.resources
import pyvisa.constants

import logging
import logging.handlers

import time
import numpy as np

class Keithley6430:
	def __init__(self, instrument):
		self.instrument = instrument
		self.sour = "VOLT"
		self.sens = "RES"
		
	def close(self):
		self.instrument.close()
		print("session closed")
		
	def select_measure(self, meas):
		if (meas == "VOLT"):
			self.instrument.write(':SENS:FUNC "VOLT"')
			print("voltage sens chosen")
			self.sens = "VOLT"
		elif (meas == "CURR"):
			self.instrument.write(':SENS:FUNC "CURR"')
			print("current sens chosen")
			self.sens = "CURR"
		elif (meas == "RES"):	
			self.instrument.write('SENS:FUNC "RES"')
			print("resistance sens chosen")
			self.sens = "RES"
		else:
			print("inappropriate arg")
				
	def select_res_range(self, range):
		self.instrument.write(":SENS:RES:RANG " + str(range))
		
	def select_resist_mode(self,mode):
		if (mode == "MAN"):
			self.instrument.write(":SENS:RES:MODE MAN")
			print("MANUAL rsistance mode")
		elif (mode == "AUTO"):
			self.instrument.write(":SENS:RES:MODE AUTO")
			print("AUTO resistance mode")
		else:
			print("INVALID Ohm MODE!") 
	
	def switch_auto(self, mode):
		if (mode == "ON"):
			self.instrument.write(":SENS:VOLT:RANG:AUTO ON")
			print("AUTO range is ON")
		elif (mode == "OFF"):
			self.instrument.write(":SENS:VOLT:RANG:AUTO OFF")
			print("AUTO range is OFF")
		else:
			print("INVALID VOLT MODE!")
	
	def select_source(self, option):
	#	with DEVICELOCK:
		if (option == "VOLT"):
			self.instrument.write(":SOUR:FUNC VOLT")
			self.sour = option
			print("VOLT source chosen")
		elif (option == "CURR"):
			self.instrument.write(":SOUR:FUNC CURR")
			self.sour = option
			print("CURR source chosen")
		else:
			logging.info("inappropriate arg")

	def set_source_range(self, R):
		self.instrument.query(":SOUR:" + self.sour + ":RANG " + str(R))
		if (self.sour == "VOLT"):
			ch = "mV"
		else:
			ch = "mA"
		print(f"Source range is {R/1e-3} {R}")


	def set_source_level(self, L):
		self.instrument.write(":SOUR:" + self.sour + ":LEV " + str(L))
		if (self.sour == "VOLT"):
			ch = "mV"
		else:
			ch = "mA"
		print(f"Source level is {L/1e-3} {ch}")

	def set_compl(self, I, V):
		self.instrument.write(":SENS:CURR:PROT " + str(I))
		self.instrument.write(":SENS:VOLT:PROT " + str(V))
		print(f"Current compl. is {I/1e-3} mA\nVoltage compl. is {V/1e-3} mV")

	def set_meas_range(self, R):
		self.instrument.write(":SENS:" + self.sens + ":RANG " + str(R))
		if (self.sens == "VOLT"):
			ch = "mV"
			R /= 1e-3
		elif (self.sens == "CURR"):
			ch = "mA"
			R /= 1e-3
		else: 
			ch = "kOhm"
			R /= 1e6
		print(f"Sense range is {R} {ch}")
		
	def set_comp(self, status):
		self.instrument.write(":SENS:RES:OCOM " + status)
		print("offset compensation is " + status)

	def read(self):
		self.instrument.write(":OUTP ON")
		print("\t ON")
		ans = self.instrument.query(":READ?")
		self.instrument.write(":OUTP OFF")
		print("\t OFF")
		ans = [float(x) for x in ans.split(",")]
		return {"V":ans[0], "I":ans[1], "R":ans[2], "G1":ans[3], "G2":ans[4]}



if __name__ == "__main__":
	rm = pyvisa.ResourceManager()
	print(rm.list_resources())

	# 57600 8O1
	kinstr = rm.open_resource("ASRL7::INSTR")
	
	print("Sending *IDN?...")
	print(kinstr.query("*IDN?"))   
	k = Keithley6430(kinstr)

	k.select_source("CURR")
	
	k.set_source_level(3e-6)	
		
	k.close()
	
	
	
	print("DOOM.")

