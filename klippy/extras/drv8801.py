# Add DRV8801's controls and inputs 
#
# Copyright (C) 2020  Victor HAYOT <33vic.h@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

#TO DO : read the correct current value

import logging

ADC_REPORT_TIME = 0.015
ADC_SAMPLE_TIME = 0.001
ADC_SAMPLE_COUNT = 8

UP = 1.
DOWN = 0.

PIN_MIN_TIME = 0.1
	
class Drv8801:
	def __init__(self, config):
		self.printer = config.get_printer()
		self.toolhead = self.ppins =  None
		self.motor_name = config.get_name().split()[-1]
		self.printer.register_event_handler("klippy:ready", self._handle_ready)
		self.printer.register_event_handler("DRV8801:stalled", self._handle_stall)
		self.reactor = self.printer.get_reactor()
		
		self.lastIsensReading = 0.
		self.last_value_time = 0.
		self.lastdirection = UP
		self.isens_triggered = False
		
		#pins setup
		ppins = self.printer.lookup_object('pins')
		self.mcu_speedpin = ppins.setup_pin('pwm', config.get('SPEEDpin'))
		self.mcu_speedpin.setup_max_duration(0.)#may want to give it a max_duration > 0, to catch a clamping failure ?
		self.mcu_dirpin = ppins.setup_pin('digital_out', config.get('DIRpin'))
		self.mcu_dirpin.setup_max_duration(0.)
		
		#config parameters
		self.mincurrent = config.getfloat('minimum_current' ,0. ) 
		self.maxcurrent = config.getfloat('maximum_current' ,3.,above=self.mincurrent )
		self.isens_trigger = config.getfloat('current_trigger', 1.5, above=0.)##nom de ligne, defaut, critere
		
		# Start adc
		self.mcu_isens = ppins.setup_pin('adc', config.get('Isenspin'))
		self.mcu_isens.setup_adc_callback(ADC_REPORT_TIME, self.adc_callback)
		self.mcu_isens.setup_minmax(ADC_SAMPLE_TIME, ADC_SAMPLE_COUNT,self.mincurrent,self.maxcurrent)
		query_adc = self.printer.load_object(config, 'query_adc')
		query_adc.register_adc(self.motor_name, self.mcu_isens)
		# isens value updating 
		self.isens_value_update_timer = self.reactor.register_timer(self.isens_value_update_event)
		
		# Register commands
		self.gcode = self.printer.lookup_object('gcode')
		#DRV_STATUS DRV8801=name"
		self.gcode.register_mux_command("DRV_STATUS", "DRV8801", self.motor_name,
                                   self.cmd_DRV8801_STATUS,
                                   desc=self.cmd_DRV8801_STATUS_help)		
		#"QUERY_CURRENT DRV8801=name"							
		self.gcode.register_mux_command("QUERY_CURRENT", "DRV8801", self.motor_name,
                                   self.cmd_QUERY_CURRENT,
                                   desc=self.cmd_QUERY_DRV8801_CURRENT_help)
		#"DRIVE_UNTIL_STALL DRV8801=name"
		self.gcode.register_mux_command("DRIVE_UNTIL_STALL", "DRV8801", self.motor_name,
                                   self.cmd_DRIVE_UNTIL_STALL,
                                   desc=self.cmd_DRIVE_UNTIL_STALL_help)
		
		#"CLAMP_UP DRV8801=name"
		self.gcode.register_mux_command("CLAMP_UP", "DRV8801", self.motor_name,
                                   self.cmd_CLAMP_UP,
                                   desc=self.cmd_CLAMP_UP_help)
								   
		#"CLAMP_DOWN DRV8801=name"
		self.gcode.register_mux_command("CLAMP_DOWN", "DRV8801", self.motor_name,
                                   self.cmd_CLAMP_DOWN,
                                   desc=self.cmd_CLAMP_DOWN_help)
		
		#"DRV_RESET DRV8801=name"
		self.gcode.register_mux_command("DRV_RESET", "DRV8801", self.motor_name,
                                   self.cmd_DRV_RESET,
                                   desc=self.cmd_DRV_RESET_help)
 
	def _handle_ready(self):
		# Start extrude factor update timer
		self.toolhead = self.printer.lookup_object('toolhead')
		self.reactor.update_timer(self.isens_value_update_timer,self.reactor.NOW)
	
	def _handle_stall(self):
		# cut the power to the motor
		print_time = self.printer.lookup_object('toolhead').get_last_move_time()
		print_time = max(print_time, self.last_value_time + PIN_MIN_TIME)
		self.mcu_speedpin.set_pwm(print_time, 0.)
		self.last_value_time = print_time

		logging.info("clamp shut off")
		
	def adc_callback(self, read_time, read_value):
        # read sensor value
		self.lastIsensReading = round(read_value*2 ,5)#0.5V = 1A
		
		logging.info("current: %f at Time %.2f" %, read_time, self.lastIsensReading)
		
	def isens_value_update_event(self, eventtime):
		self.isens_triggered = self.lastIsensReading > self.isens_trigger
		if self.isens_triggered :
			self.printer.send_event("DRV8801:stalled")
		return eventtime + 0.15#will execute once more in a second. Might try to reduce this interval
	
	cmd_DRV8801_STATUS_help = "Has the DRV8801 current trigger tripped ?"	
	def cmd_DRV8801_STATUS(self, gcmd):
		response = ""
		if self.isens_triggered :
			response = response + "Tripped"
		else : 
			response = response + "Not tripped"
		gcmd.respond_info(response)	
		
	cmd_QUERY_DRV8801_CURRENT_help = "print the output of the Isens pin on the DRV8801 motor driver"	
	def cmd_QUERY_CURRENT(self, gcmd):
		response = "current = " + str(self.lastIsensReading)
		gcmd.respond_info(response)
		
	cmd_DRIVE_UNTIL_STALL_help = "move the motor until it draws a predetermined amount of current"
	def cmd_DRIVE_UNTIL_STALL(self, gcmd):##WIP
		direction = DOWN
		if self.lastdirection == direction:
			direction = UP
		self.lastdirection = direction
		print_time = self.printer.lookup_object('toolhead').get_last_move_time()
		print_time = max(print_time, self.last_value_time + PIN_MIN_TIME)
	
		self.mcu_dirpin.set_digital(print_time, direction)
		#gcmd.respond_info(str(print_time))
		self.mcu_speedpin.set_pwm(print_time, 1.)
		self.last_value_time = print_time
	
	cmd_CLAMP_UP_help = "move the motor up"
	def cmd_CLAMP_UP(self, gcmd):
		direction = UP
		print_time = self.printer.lookup_object('toolhead').get_last_move_time()
		print_time = max(print_time, self.last_value_time + PIN_MIN_TIME)
	
		self.mcu_dirpin.set_digital(print_time, direction)
		self.mcu_speedpin.set_pwm(print_time, 1.)
		
		self.last_value_time = print_time	
		
	cmd_CLAMP_DOWN_help = "move the motor down"
	def cmd_CLAMP_DOWN(self, gcmd):
		direction = DOWN
		print_time = self.printer.lookup_object('toolhead').get_last_move_time()
		print_time = max(print_time, self.last_value_time + PIN_MIN_TIME)
	
		self.mcu_dirpin.set_digital(print_time, direction)
		self.mcu_speedpin.set_pwm(print_time, 1.)
		
		self.last_value_time = print_time	
		
	cmd_DRV_RESET_help = "reset the speed pin of the driver"
	def cmd_DRV_RESET(self, gcmd):
		print_time = self.printer.lookup_object('toolhead').get_last_move_time()
		print_time = max(print_time, self.last_value_time + PIN_MIN_TIME)
		self.mcu_speedpin.set_pwm(print_time, 0.)
		self.last_value_time = print_time
		
def load_config_prefix(config):
    return Drv8801(config)