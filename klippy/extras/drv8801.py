# Add DRV8801's controls and inputs 
#
# Copyright (C) 2020  Victor HAYOT <33vic.h@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

#Code_Overwiew.md est ma bible
#Pour l'ajout de module supplémentaire, s'inspirer de "servo.py"

ADC_REPORT_TIME = 0.500
ADC_SAMPLE_TIME = 0.001
ADC_SAMPLE_COUNT = 8

UP = 1
DOWN = 0

PIN_MIN_TIME = 0.100

class DRV8801:
	def __init__(self, config):
	self.printer = config.get_printer()
	self.toolhead = self.ppins =  None
	self.printer.register_event_handler("klippy:ready", self.handle_ready)
	self.reactor = self.printer.get_reactor()
	self.lastIsensReading = 0
	self.last_value_time = 0.
	#pins setup
	ppins = self.printer.lookup_object('pins')
    self.mcu_speedpin = ppins.setup_pin('pwm', config.get('SPEEDpin'))
	self.mcu_dirpin = ppins.setup_pin('digital_out', config.get('DIRpin'))
	#config parameters
	self.isens_trigger = config.getfloat('current_trigger', 1.5, above=0.))##nom de ligne, défaut, critère
	self.mincurrent = config.getfloat('minimum_current' ,0 ) 
	self.maxcurrent = config.getfloat('maximum_current' ,3,above=self.mincurrent ) 
	# Start adc
	self.mcu_isens = ppins.setup_pin('adc', config.get('Isenspin'))
	self.mcu_isens.setup_minmax(ADC_SAMPLE_TIME, ADC_SAMPLE_COUNT,self.mincurrent,self.maxcurrent)
    self.mcu_isens.setup_adc_callback(ADC_REPORT_TIME, self.adc_callback)
	# isens value updating 
	self.isens_value_update_timer = self.reactor.register_timer(self.isens_value_update_event)
	# Register commands
    self.gcode = self.printer.lookup_object('gcode')
    self.gcode.register_command('QUERY_DRV8801_CURRENT', self.cmd_QUERY_CURRENT)
    self.gcode.register_command('DRIVE_UNTIL_TRIGGER',
                                    self.cmd_DRIVE_UNTIL_TRIGGER)
    def handle_ready(self):
		# Start extrude factor update timer
		self.toolhead = self.printer.lookup_object('toolhead')
        self.reactor.update_timer(self.isens_value_update_timer,
                                  self.reactor.NOW)
	
	def adc_callback(self, read_time, read_value):
        # read sensor value
        self.lastIsensReading = round(read_value , 1)
	def isens_value_update_event(self, eventtime):
		self.isens_triggered = self.lastIsensReading > self.isens_trigger
		return eventtime + 1	
		
	def cmd_QUERY_CURRENT(self, gcmd):
		response = "current = "
                         + str(self.lastIsensReading)+("/0.5")

	def cmd_DRIVE_UNTIL_TRIGGER(self, gcmd):##WIP
		direction = DOWN
		if self.lastdirection == direction:
			direction = UP
        print_time = self.printer.lookup_object('toolhead').get_last_move_time()
        print_time = max(print_time, self.last_value_time + PIN_MIN_TIME)
        self.mcu_pin.set_digital(print_time, direction)
		while self.isens_triggered = False:
			???
		self.mcu_pin.set_digital(print_time, direction)	
        self.last_value = value
        self.last_value_time = print_time
        
def load_config_prefix(config):
    return DRV8801(config)
