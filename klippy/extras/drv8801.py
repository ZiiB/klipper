# Add DRV8801's controls and inputs 
#
# Copyright (C) 2020  Victor HAYOT <33vic.h@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

#TO DO : read the correct current value

ADC_REPORT_TIME = 0.015
ADC_SAMPLE_TIME = 0.001
ADC_SAMPLE_COUNT = 8

UP = 1
DOWN = 0

PIN_MIN_TIME = 0.100
	
class Drv8801:
	def __init__(self, config):
		self.printer = config.get_printer()
		self.toolhead = self.ppins =  None
		self.motor_name = config.get_name().split()[-1]
		self.printer.register_event_handler("klippy:ready", self._handle_ready)
		self.reactor = self.printer.get_reactor()
		
		self.lastIsensReading = 0.
		self.last_value_time = 0.
		self.lastdirection = UP
		self.isens_triggered = False
		
		#pins setup
		ppins = self.printer.lookup_object('pins')
		self.mcu_speedpin = ppins.setup_pin('pwm', config.get('SPEEDpin'))
		self.mcu_dirpin = ppins.setup_pin('digital_out', config.get('DIRpin'))
		
		#config parameters
		self.mincurrent = config.getfloat('minimum_current' ,0. ) 
		self.maxcurrent = config.getfloat('maximum_current' ,3.,above=self.mincurrent )
		self.isens_trigger = config.getfloat('current_trigger', 1.5, above=0.)##nom de ligne, defaut, critere
		
		# Start adc
		self.mcu_isens = ppins.setup_pin('adc', config.get('Isenspin'))
		self.mcu_isens.setup_minmax(ADC_SAMPLE_TIME, ADC_SAMPLE_COUNT,self.mincurrent,self.maxcurrent)
		self.mcu_isens.setup_adc_callback(ADC_REPORT_TIME, self.adc_callback)
		
		# isens value updating 
		self.isens_value_update_timer = self.reactor.register_timer(self.isens_value_update_event)
		
		# je ne sais pas ce que je fais, j'essaie d'implanter la facon dont est gere le home
		#self._move_completion = self.reactor.register_callback(self._stall_retry)
		
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
		#"DRIVE_UNTIL_TRIGGER DRV8801=name"
		self.gcode.register_mux_command("DRIVE_UNTIL_TRIGGER", "DRV8801", self.motor_name,
                                   self.cmd_DRIVE_UNTIL_TRIGGER,
                                   desc=self.cmd_DRIVE_UNTIL_TRIGGER_help)
		
	def _handle_ready(self):
		# Start extrude factor update timer
		self.toolhead = self.printer.lookup_object('toolhead')
		self.reactor.update_timer(self.isens_value_update_timer,self.reactor.NOW)
								  
	def adc_callback(self, read_time, read_value):
        # read sensor value
		self.lastIsensReading = round(read_value , 1)
		
	def isens_value_update_event(self, eventtime):
		self.isens_triggered = self.lastIsensReading > self.isens_trigger
		return eventtime + 1#will execute once more in a second	
	
	"""def _stall_retry(self, eventtime):
		self._trigger_completion = self._reactor.completion()
		#keep the motor moving until current trigger trips
        while 1:
            did_trigger = self._trigger_completion.wait(eventtime + 0.100)
            if did_trigger is not None:
                # Motor stalled
                return True
            # Check for timeout
            last = self._mcu.estimated_print_time(self.last_value_time)
            if last > self._home_end_time or self._mcu.is_shutdown():
                return False"""

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
		response = "current = " + str(self.lastIsensReading)+("/0.5")
		gcmd.respond_info(response)
		
	cmd_DRIVE_UNTIL_TRIGGER_help = "move the motor until it draws a predetermined amount of current"
	def cmd_DRIVE_UNTIL_TRIGGER(self, gcmd):##WIP
		## could wake up the callback at the start..
		direction = DOWN
		if self.lastdirection == direction:
			direction = UP
		self.lastdirection = direction
		print_time = self.printer.lookup_object('toolhead').get_last_move_time()
		print_time = max(print_time, self.last_value_time + PIN_MIN_TIME)
		self.mcu_dirpin.set_digital(print_time, direction)
		while self.isens_triggered == False:
			## ..check when it triggers..
			print_time=print_time+0.015
			isens_value_update_event(print_time)
			self.mcu_speedpin.set_pwm(print_time, 255)
		self.mcu_speedpin.set_digital(print_time, 0 )	
		self.last_value = value
		self.last_value_time = print_time
		##..Then put it to sleep until the next cycle.
		
        
def load_config_prefix(config):
    return Drv8801(config)