import sys, os, time, json, queue
import datetime
import board, busio
import serial
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import adafruit_character_lcd.character_lcd_i2c as character_lcd
import MAX6675
from hx711 import HX711
import random
import threading

global g_print_lcd_output_door_topic
g_print_lcd_output_door_topic = ''

global g_print_lcd_output_door_msg
g_print_lcd_output_door_msg = ''

global g_print_lcd_safe_door_topic
g_print_lcd_safe_door_topic = ''

global g_print_lcd_safe_door_msg
g_print_lcd_safe_door_msg = ''

q = queue.Queue()
global buzzer_running
buzzer_running = 0
global arr_count
arr_count = 5
global bottom_temp_arr, top_temp_arr
bottom_temp_arr = [0,0,0,0,0]
top_temp_arr = [0,0,0,0,0]


#---SET Pin-------------------------------------------------------------
# Switch
Debug_switch_pin = 16 # Debug Switch : Digital_Input_3
SW4_pin = 38 # Start Button : Digital_Input_2
Push_SW_pin = 38 # Start Button : Digital_Input_8
Select_SW = 6 # Select Switch : Digital_Input_7

# Load Cell (Direct)
DAT = 34
CLK = 35

# LCD I2C 
SDA = 30 # SDA_LCD-DAT 28
SCL = 31 # SCL_LCD-CLK 27

# Digital IN
Input_Door_pin = 7 # Input Door Sensor() : Digital_Input_4
Output_Door_pin = 10 # Output Door Sensor() : Digital_Input_5
Safe_Door_pin = 11 # Safe Door Sensor(Front Door) : Digital_Input_6

# Digital OUT (Arduino)
Heat_12 = 13 # Digital_Output_12
Heat_3 = 12 # Digital_Output_11
Heat_4 = 11 # Digital_Output_10
Mix_motor = 10 # Digital_Output_13(red)
Cooling_motor = 9 # Digital_Output_14
Sol_val = 6 # Digital_Output_15
Buzzer = 5

# Temperature 1 Top
CLK1 = 27 # Digital_Input_9
CS1  = 26 # Digital_Input_10
SO1  = 17 # Digital_Input_11

# Temperature 2 Bottom
CLK2 = 41 # Digital_Input_12
CS2  = 40 # Digital_Input_13
SO2  = 39 # Digital_Input_14

#---SET GPIO------------------------------------------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
# Switch
GPIO.setup(Debug_switch_pin, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(SW4_pin, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(Push_SW_pin, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(Select_SW, GPIO.IN, GPIO.PUD_UP)
# Door
GPIO.setup(Input_Door_pin, GPIO.IN,GPIO.PUD_UP)
GPIO.setup(Output_Door_pin, GPIO.IN,GPIO.PUD_UP)
GPIO.setup(Safe_Door_pin, GPIO.IN,GPIO.PUD_UP)

#---GET Door------------------------------------------------------------
def get_input_door(Input_Door_pin):
	input_door = GPIO.input(Input_Door_pin)
	json_input_door = val_to_json(input_door)

	return (json_input_door)


def get_output_door(Output_Door_pin):
	output_door = GPIO.input(Output_Door_pin)
	json_output_door = val_to_json(output_door)

	return (json_output_door)


def get_safe_door(Safe_Door_pin):
	safe_door = GPIO.input(Safe_Door_pin)
	json_safe_door = val_to_json(safe_door)

	return (json_safe_door)
#-----------------------------------------------------------------------

#---Operation Mode------------------------------------------------------
def Operation(Select_SW):
	sel_sw = GPIO.input(Select_SW)
	sel_sw = val_to_json(sel_sw)

	return (sel_sw)

#---Start Button--------------------------------------------------------
def start_btn(SW4_pin):
	SW4 = GPIO.input(SW4_pin)
	SW4 = val_to_json(SW4)

	return (SW4)

# Temperature
sensor1 = MAX6675.MAX6675(CLK1, CS1, SO1)
sensor2 = MAX6675.MAX6675(CLK2, CS2, SO2)

#---GET Temperature-----------------------------------------------------
def get_temp():
	global avg_bottom_temp, avg_top_temp
	top_temp = round(sensor1.readTempC(), 1)
	bottom_temp = round(sensor2.readTempC(), 1)

	for i in range(arr_count):
		if (i > 0):
			bottom_temp_arr[i-1] = bottom_temp_arr[i]
			top_temp_arr[i-1] = top_temp_arr[i]
		bottom_temp_arr[arr_count-1] = bottom_temp
		top_temp_arr[arr_count-1] = top_temp

	avg_bottom_temp = round((sum(bottom_temp_arr) / arr_count), 2)
	avg_top_temp = round((sum(top_temp_arr) / arr_count), 2)

	temperature1 = val_to_json(avg_top_temp, avg_bottom_temp)

	return (temperature1)

#---Debug Button--------------------------------------------------------
def debug_mode(Debug_switch_pin):
	debug_val = GPIO.input(Debug_switch_pin)

	debug_val = val_to_json(debug_val)

	return (debug_val)

#---SET Load Cell & GET Weight------------------------------------------
def cleanAndExit():
    print("Cleaning...")

    if not EMULATE_HX711:
        GPIO.cleanup()

    print("Bye!")
    sys.exit()


def init_loadcell(referenceUnit = 1):
	global hx
	global nWeightCount
	nWeightCount = 1

	hx = HX711(34, 35)
	hx.set_reading_format("MSB", "MSB")
	hx.set_reference_unit(referenceUnit)
	hx.reset()


def set_factor(referenceUnit):
	hx.set_reference_unit(referenceUnit)
	hx.reset()


def calc_ref_Unit(reference_weight, set_ref_Unit):
	ref_weight_total = 0

	for i in range(nWeightCount):
		weight = hx.get_weight(5)
		ref_weight_total += weight

	avg_ref_weight = (ref_weight_total / nWeightCount)
	cur_weight = (avg_ref_weight - avg_zero_weight)
	cur_weight = max(0, float(cur_weight))
	cur_factor = (cur_weight / reference_weight)


	if (cur_factor == 0.0):
		cur_factor = set_ref_Unit

	hx.set_reference_unit(cur_factor)
	hx.reset()

	factor_weight_total = 0

	for i in range(nWeightCount):
		weight = hx.get_weight(5)
		factor_weight_total += weight

	avg_factor_weight = (factor_weight_total / nWeightCount)
	avg_factor_weight = max(0, float(avg_factor_weight))
	correlation_value = avg_factor_weight - reference_weight
	factor = {"factor":cur_factor, "correlation_value":correlation_value}

	with open ("./factor.json", "w") as factor_json:
		json.dump(factor, factor_json)

	print("Complete!")

	calc_ref_unit = val_to_json(cur_factor, correlation_value)

	return calc_ref_unit


def get_loadcell():
	global flag
	global weight_arr

	try:
		if (flag == 0):
			for i in range(arr_count):
				weight = hx.get_weight(5)
				weight_arr[i] = weight
				flag = 1
		else:
			weight = hx.get_weight(5)
			for i in range(arr_count):
				if (i > 0):
					weight_arr[i-1] = weight_arr[i]
				weight_arr[arr_count-1] = weight

		avg_weight = round((sum(weight_arr) / arr_count), 2)
		final_weight = avg_weight - correlation_value
		final_weight = max(0, float(final_weight))
		weight_json = val_to_json(final_weight)

	except (KeyboardInterrupt, SystemExit):
		cleanAndExit()

	return (weight_json)


def ref_weight(tare_weight):
	global reference_weight
	reference_weight = tare_weight

	val = val_to_json(1)

	init_loadcell(1)
	global avg_zero_weight
	zero_weight = 0
	for i in range(5):
		weight = hx.get_weight(5)
		zero_weight += weight

	avg_zero_weight = (zero_weight / 5)
	avg_zero_weight = max(0, float(avg_zero_weight))

	print("Add weight for initialize...")

	return val
#-----------------------------------------------------------------------


#---Serial Communication with Arduino-----------------------------------
def Serial_Feather(pin=None, pin2=None, pin3=None, val=None, val2=None, val3=None):
	if (pin != None and pin2 == None and pin3 == None):
		ser_msg = ('<' + str(pin) + ',' + str(val) + '>\n').encode()
		#print(ser_msg)
		ser.write(ser_msg)
	elif (pin != None and pin2 != None and pin3 != None):
		ser_msg = ('<' + str(pin) + ',' + str(val) + '/' + str(pin2) + ',' + str(val2) + '/' + str(pin3) + ',' + str(val3) + '>\n').encode()
		#print(ser_msg)
		ser.write(ser_msg)
#-----------------------------------------------------------------------

#---Heater--------------------------------------------------------------
def heater(Heat_12, Heat_3, Heat_4, val, val2, val3):
	Serial_Feather(pin=Heat_12, pin2=Heat_3, pin3=Heat_4, val=val, val2=val2, val3=val3)

#---Buzzer--------------------------------------------------------------
def buzzer(Buzzer, val):
	Serial_Feather(pin=Buzzer, val=val)
	#print ("Beep")

#---Solenoid------------------------------------------------------------
def solenoid(Sol_val, val):
	Serial_Feather(pin=Sol_val, val=val)

#---Fan-----------------------------------------------------------------
def fan(Cooling_motor, val):
	Serial_Feather(pin=Cooling_motor, val=val)

#---Stirrer-------------------------------------------------------------
def stirrer(Mix_motor, val):
	Serial_Feather(pin=Mix_motor, val=val)

def json_to_val(json_val):
	payloadData = json.loads(json_val)

	if (len(payloadData) == 1):
		val = payloadData['val']
		return (val)
	elif (len(payloadData) == 2):
		val = payloadData['val']
		val2 = payloadData['val2']
		return (val, val2)
	elif (len(payloadData) == 3):
		val = payloadData['val']
		val2 = payloadData['val2']
		val3 = payloadData['val3']
		return (val, val2, val3)	

def val_to_json(val,val2=None):
	if (val2 != None):
		json_val = {"val":val,"val2":val2}
	else:
		json_val = {"val":val}
	json_val = json.dumps(json_val)
	
	return (json_val)
	
#---MQTT----------------------------------------------------------------

def on_connect(client,userdata,flags, rc):
	print('[dry_mqtt_connect] connect to ', broker_address)


def on_disconnect(client, userdata, flags, rc=0):
	print(str(rc))


def on_subscribe(client, userdata, mid, granted_qos):
	print("subscribed: " + str(mid) + " " + str(granted_qos))


def func_set_q(f_msg):
	if(f_msg.topic == '/set_buzzer'):
		if(buzzer_running == 0):
			q.put_nowait(f_msg)
			#q.put(f_msg)

# 	elif (msg.topic == '/req_debug_mode'):
#         #print("topic: ", msg.topic)
# 		deb = debug_mode(Debug_switch_pin)
# 		dry_client.publish("/res_debug_mode", deb)
#
# 	elif (msg.topic == '/req_start_btn'):
# 		#print("topic: ", msg.topic)
# 		sw4_json = start_btn(SW4_pin)
# 		dry_client.publish("/res_start_btn", sw4_json)
#
# 	elif (msg.topic == '/req_input_door'):
# 		#print("topic: ", msg.topic)
# 		json_input_door = get_input_door(Input_Door_pin)
# 		#print('input door: ', json_input_door)
# 		dry_client.publish("/res_input_door", json_input_door)
#
# 	elif (msg.topic == '/req_output_door'):
# 		#print("topic: ", msg.topic)
# 		json_output_door = get_output_door(Output_Door_pin)
# 		#print("output door: ", json_output_door)
# 		dry_client.publish("/res_output_door", json_output_door)
#
# 	elif (msg.topic == '/req_safe_door'):
# 		#print("topic: ", msg.topic)
# 		json_safe_door = get_safe_door(Safe_Door_pin)
# 		#print("safe door: ", json_safe_door)
# 		dry_client.publish("/res_safe_door", json_safe_door)
#
# 	elif (msg.topic == '/req_operation_mode'):
# 		#print("topic: ", msg.topic)
# 		json_operation_mode = Operation(Select_SW)
# 		#print("operation: ", json_operation_mode)
# 		dry_client.publish("/res_operation_mode", json_operation_mode)

# 	elif (msg.topic == '/req_internal_temp'):
# 	    #print("topic: ", msg.topic)
# 	    temperature = get_temp()
# 	    dry_client.publish("/res_internal_temp", temperature)
#
#     elif (msg.topic == '/req_zero_point'):
#         #print("topic: ", msg.topic)
#         data = msg.payload.decode('utf-8').replace("'", '"')
#         reference_weight = json.loads(data)
#         reference_weight = reference_weight['val']
#         #print ("reference_weight: ", reference_weight)
#         val = ref_weight(reference_weight)
# 		dry_client.publish("/res_zero_point", val)
#
#     elif (msg.topic == '/req_calc_factor'):
#         #print("topic: ", msg.topic)
#         calc_referenceUnit = calc_ref_Unit(reference_weight, set_ref_Unit)
#         dry_client.publish("/res_calc_factor", calc_referenceUnit)
#
#     elif (msg.topic == '/req_weight'):
#         #print("topic: ", msg.topic)
#         weight = get_loadcell()
#         #print(weight)
#         dry_client.publish("/res_weight", weight)
#
#     elif (msg.topic == '/print_lcd_internal_temp'):
#         #print("topic: ", msg.topic)
#         data = msg.payload.decode('utf-8').replace("'", '"')
#         top, bottom = json_to_val(data)
#         #print ('print_lcd: ', top, ' ', bottom)
#         displayTemp(top, bottom)
#
#     elif (msg.topic == '/print_lcd_state'):
#         #print("topic: ", msg.topic)
#         data = msg.payload.decode('utf-8').replace("'", '"')
#         state = json_to_val(data)
#         displayState(state)
#         print('print_lcd_state')
#
#     elif (msg.topic == '/print_lcd_debug_message'):
#         #print("topic: ", msg.topic)
#         data = msg.payload.decode('utf-8').replace("'", '"')
#         debug = json_to_val(data)
#         #print (debug)
#         displayMsg(debug)
#
#     elif (msg.topic == '/print_lcd_loadcell'):
#         #print("topic: ", msg.topic)
#         data = msg.payload.decode('utf-8').replace("'", '"')
#         loadcell, target_loadcell = json_to_val(data)
#         loadcell = str(loadcell)
#         #print(loadcell, ' ', target_loadcell)
#         target_loadcell = str(target_loadcell)
#         #loadcell = (loadcell[2:(len(loadcell)-5)])
#         #target_loadcell = (target_loadcell[2:(len(target_loadcell)-5)])
#         displayLoadcell(loadcell, target_loadcell)
#
#     elif (msg.topic == '/print_lcd_loadcell_factor'):
#         #print("topic: ", msg.topic)
#         data = msg.payload.decode('utf-8').replace("'", '"')
#         loadcell_factor, corr_val = json_to_val(data)
#         displayLoadcellFactor(loadcell_factor)
#
#     elif (msg.topic == '/print_lcd_input_door'):
#         #print("topic: ", msg.topic)
#         data = msg.payload.decode('utf-8').replace("'", '"')
#         input_door = json_to_val(data)
#         displayInputDoor(input_door)
#
#     elif (msg.topic == '/print_lcd_output_door'):
#         #print("topic: ", msg.topic)
#         data = msg.payload.decode('utf-8').replace("'", '"')
#         output_door = json_to_val(data)
#         displayOutputDoor(output_door)
#
#     elif (msg.topic == '/print_lcd_safe_door'):
#         #print("topic: ", msg.topic)
#         data = msg.payload.decode('utf-8').replace("'", '"')
#         val_safe_door = json_to_val(data)
#         displaySafeDoor(val_safe_door)
#
#     elif (msg.topic == '/print_lcd_elapsed_time'):
#         #print("topic: ", msg.topic)
#         data = msg.payload.decode('utf-8').replace("'", '"')
#         elapsed_time = json_to_val(data)
#         elapsed_time = str(datetime.timedelta(seconds=elapsed_time))
#         displayElapsed(elapsed_time)

	elif (f_msg.topic == '/set_solenoid'):
		#print("topic: ", f_msg.topic)
		data = f_msg.payload.decode('utf-8').replace("'", '"')
		solenoid_val = json_to_val(data)
		solenoid(Sol_val, solenoid_val)

	elif (f_msg.topic == '/set_fan'):
		#print("topic: ", f_msg.topic)
		data = f_msg.payload.decode('utf-8').replace("'", '"')
		fan_val = json_to_val(data)
		fan(Cooling_motor, fan_val)

	elif (f_msg.topic == '/set_heater'):
		#print("topic: ", f_msg.topic)
		data = f_msg.payload.decode('utf-8').replace("'", '"')
		heat_val, heat_val2, heat_val3 = json_to_val(data)
		heater(Heat_12, Heat_3, Heat_4, heat_val, heat_val2, heat_val3)

	elif (f_msg.topic == '/set_stirrer'):
		#print("topic: ", f_msg.topic)
		data = f_msg.payload.decode('utf-8').replace("'", '"')
		stirrer_val = json_to_val(data)
		stirrer(Mix_motor, stirrer_val)

#     elif (f_msg.topic == '/set_buzzer'):
#         #print("topic: ", f_msg.topic)
#         buzzer_running = 1
#         data = f_msg.payload.decode('utf-8').replace("'", '"')
#         buzzer_val = json_to_val(data)
#         buzzer(Buzzer, buzzer_val)
#         buzzer_running = 0

#     elif (f_msg.topic == '/set_zero_point'):
#         #print("topic: ", f_msg.topic)
#         data = f_msg.payload.decode('utf-8').replace("'", '"')
#         set_ref_Unit, set_corr_val = json_to_val(data)
#         #print('set_zero_point - ',set_ref_Unit, ', ', set_corr_val)
#         set_ref_Unit = float(set_ref_Unit)
#         correlation_value = float(set_corr_val)
#         set_factor(set_ref_Unit)

	else: 
		q.put_nowait(f_msg)
		#q.put(f_msg)



def on_message(client, userdata, _msg):
# 	if(msg.topic == '/print_lcd_output_door'):
# 		g_print_lcd_output_door_topic = msg.topic
# 		g_print_lcd_output_door_msg = msg.payload.decode('utf-8').replace("'", '"')
#
# 	elif(msg.topic == '/print_lcd_safe_door'):
# 		g_print_lcd_safe_door_topic = msg.topic
# 		g_print_lcd_safe_door_msg = msg.payload.decode('utf-8').replace("'", '"')
#
# 	else:
	func_set_q(_msg)
#-----------------------------------------------------------------------

#---INIT LCD & Display Message------------------------------------------
def lcd_init():
	lcd_columns = 20
	lcd_rows = 4

	i2c = busio.I2C(board.SCL, board.SDA)

	lcd = character_lcd.Character_LCD_I2C(i2c, lcd_columns, lcd_rows)
	lcd.backlight = True

	return lcd


def displayState(msg1):
	print(msg1)
	if (len(str(msg1)) > 5):
		msg1 = str(msg1)
		msg1 = msg1[0:5]
	try:
		if (msg1 == 'DEBUG'):
			g_lcd.clear()
		g_lcd.cursor_position(0,0)
		message = '     '
		g_lcd.message = message
		g_lcd.cursor_position(0,0)
		g_lcd.message = f'{msg1}'
	except OSError:
		lcd_init()
		if (msg1 == 'DEBUG'):
			g_lcd.clear()
		g_lcd.cursor_position(0,0)
		message = '     '
		g_lcd.message = message
		g_lcd.cursor_position(0,0)
		g_lcd.message = f'{msg1}'


def displayTemp(msg1, msg2):
	if (len(str(msg1)) > 5):
		msg1 = str(msg1)
		msg1 = msg1[0:5]
	elif (len(str(msg2)) > 5):
		msg2 = str(msg2)
		msg2 = msg2[0:5]
	try:
		g_lcd.cursor_position(8,0)
		message = '     '
		g_lcd.message = message
		g_lcd.cursor_position(8,0)
		g_lcd.message = f'{msg1}'
		g_lcd.cursor_position(14,0)
		message = '     '
		g_lcd.message = message
		g_lcd.cursor_position(14,0)
		g_lcd.message = f'{msg2}'
	
	except OSError:
		lcd_init()
		g_lcd.cursor_position(8,0)
		message = '     '
		g_lcd.message = message
		g_lcd.cursor_position(8,0)
		g_lcd.message = f'{msg1}'
		g_lcd.cursor_position(14,0)
		message = '     '
		g_lcd.message = message
		g_lcd.cursor_position(14,0)
		g_lcd.message = f'{msg2}'

				
		
def displayLoadcell(msg1, msg2):
	if (len(str(msg1)) > 5):
		msg1 = str(msg1)
		msg1 = msg1[0:5]
	elif (len(str(msg2)) > 5):
		msg2 = str(msg2)
		msg2 = msg2[0:5]
	try:
		g_lcd.cursor_position(0,1)
		message = '          '
		g_lcd.message = message
		g_lcd.cursor_position(0,1)
		g_lcd.message = f'{msg1}'
		
		g_lcd.cursor_position(10,1)
		message = '          '
		g_lcd.message = message
		g_lcd.cursor_position(10,1)
		g_lcd.message = f'{msg2}'
	
	except OSError:
		lcd_init()
		g_lcd.cursor_position(0,1)
		message = '          '
		g_lcd.message = message
		g_lcd.cursor_position(0,1)
		g_lcd.message = f'{msg1}'
		
		g_lcd.cursor_position(10,1)
		message = '          '
		g_lcd.message = message
		g_lcd.cursor_position(10,1)
		g_lcd.message = f'{msg2}'


def displayLoadcellFactor(msg1):
	if (len(str(msg1)) > 6):
		msg1 = str(msg1)
		msg1 = msg1[0:6]

	try:
		g_lcd.cursor_position(14,1)
		message = '      '
		g_lcd.message = message
		g_lcd.cursor_position(14,1)
		g_lcd.message = f'{msg1}'
	
	except OSError:
		lcd_init()
		g_lcd.cursor_position(14,1)
		message = '      '
		g_lcd.message = message
		g_lcd.cursor_position(14,1)
		g_lcd.message = f'{msg1}'


def displayInputDoor(msg1):
	if (len(str(msg1)) > 1):
		msg1 = str(msg1)
		msg1 = msg1[0:1]
	try:
		g_lcd.cursor_position(15,2)
		message = ' '
		g_lcd.message = message
		g_lcd.cursor_position(15,2)
		g_lcd.message = f'{msg1}'
	except OSError:
		lcd_init()		
		g_lcd.cursor_position(15,2)
		message = ' '
		g_lcd.message = message
		g_lcd.cursor_position(15,2)
		g_lcd.message = f'{msg1}'
		
		
def displayOutputDoor(msg1):
	if (len(str(msg1)) > 1):
		msg1 = str(msg1)
		msg1 = msg1[0:1]
	try:

		g_lcd.cursor_position(17,2)
		message = ' '
		g_lcd.message = message
		g_lcd.cursor_position(17,2)
		g_lcd.message = f'{msg1}'
	except OSError:
		lcd_init()	
		g_lcd.cursor_position(17,2)
		message = ' '
		g_lcd.message = message
		g_lcd.cursor_position(17,2)
		g_lcd.message = f'{msg1}'
		
		
def displaySafeDoor(msg1):
	if (len(str(msg1)) > 1):
		msg1 = str(msg1)
		msg1 = msg1[0:1]
	try:
		g_lcd.cursor_position(19,2)
		message = ' '
		g_lcd.message = message
		g_lcd.cursor_position(19,2)
		g_lcd.message = f'{msg1}'
	except OSError:
		lcd_init()	
		g_lcd.cursor_position(19,2)
		message = ' '
		g_lcd.message = message
		g_lcd.cursor_position(19,2)
		g_lcd.message = f'{msg1}'


def displayElapsed(msg1):
	if (len(str(msg1)) > 8):
		msg1 = str(msg1)
		msg1 = msg1[0:8]
	try:
		g_lcd.cursor_position(0,2)
		message = '       '
		g_lcd.message = message
		g_lcd.cursor_position(0,2)
		g_lcd.message = f'{msg1}'
	except OSError:
		lcd_init()	
		g_lcd.cursor_position(0,2)
		message = '       '
		g_lcd.message = message
		g_lcd.cursor_position(0,2)
		g_lcd.message = f'{msg1}'


def displayMsg(msg1):
	if (len(str(msg1)) > 20):
		msg1 = str(msg1)
		msg1 = msg1[0:20]
	try:
		g_lcd.cursor_position(0,3)
		message = '                   '
		g_lcd.message = message
		g_lcd.cursor_position(0,3)
		g_lcd.message = f'{msg1}'
	
	except OSError:
		lcd_init()
		g_lcd.cursor_position(0,3)
		message = '                   '
		g_lcd.message = message
		g_lcd.cursor_position(0,3)
		g_lcd.message = f'{msg1}'
#-----------------------------------------------------------------------


#=======================================================================
global dry_client
broker_address = "localhost"
port = 1883

global g_lcd
g_lcd = lcd_init()

dry_client = mqtt.Client()
dry_client.on_connect = on_connect
dry_client.on_disconnect = on_disconnect
dry_client.on_subscribe = on_subscribe
dry_client.on_message = on_message
dry_client.connect(broker_address, port)

dry_client.subscribe("/print_lcd_internal_temp")
dry_client.subscribe("/print_lcd_state")
dry_client.subscribe("/print_lcd_debug_message")
dry_client.subscribe("/print_lcd_loadcell")
dry_client.subscribe("/print_lcd_loadcell_factor")
dry_client.subscribe("/print_lcd_elapsed_time")
dry_client.subscribe("/print_lcd_input_door")
dry_client.subscribe("/print_lcd_output_door")
dry_client.subscribe("/print_lcd_safe_door")
dry_client.subscribe("/req_zero_point")
dry_client.subscribe("/req_internal_temp")
dry_client.subscribe("/req_debug_mode")
dry_client.subscribe("/req_start_btn")
dry_client.subscribe("/req_calc_factor")
dry_client.subscribe("/req_input_door")
dry_client.subscribe("/req_output_door")
dry_client.subscribe("/req_safe_door")
dry_client.subscribe("/req_weight")
dry_client.subscribe("/req_operation_mode")
dry_client.subscribe("/set_solenoid")
dry_client.subscribe("/set_fan")
dry_client.subscribe("/set_heater")
dry_client.subscribe("/set_stirrer")
dry_client.subscribe("/set_buzzer")
dry_client.subscribe("/set_zero_point")

dry_client.loop_start()

global correlation_value
correlation_value = 0

loadcell_param = {"factor":6555,"correlation_value":200}

if (os. path.isfile("./factor.json") == False):
	with open("./factor.json","w") as refUnit_json:
		json.dump(loadcell_param, refUnit_json)
	loadcell_factor = loadcell_param['factor']
else:
	with open ("./factor.json", 'r') as refUnit_json:
		loadcell_factor = json.load(refUnit_json)
	loadcell_factor = loadcell_factor['factor']
	
init_loadcell(loadcell_factor)

global ser
ser = serial.Serial("/dev/ttyAMA0", 9600)

global set_ref_Unit
set_ref_Unit = 1
weight_arr = [0, 0, 0, 0, 0]
flag = 0

def mqtt_dequeue():
	while not q.empty():
		try:
			recv_msg = q.get(False)
			g_recv_topic = recv_msg.topic

			if (g_recv_topic == '/req_internal_temp'):
				#print("topic: ", g_recv_topic)
				temperature = get_temp()
				dry_client.publish("/res_internal_temp", temperature)

			elif (g_recv_topic == '/req_zero_point'):
				#print("topic: ", g_recv_topic)
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				reference_weight = json.loads(data)
				reference_weight = reference_weight['val']
				#print ("reference_weight: ", reference_weight)
				val = ref_weight(reference_weight)
				dry_client.publish("/res_zero_point", val)

			elif (g_recv_topic == '/req_calc_factor'):
				#print("topic: ", g_recv_topic)
				calc_referenceUnit = calc_ref_Unit(reference_weight, set_ref_Unit)
				dry_client.publish("/res_calc_factor", calc_referenceUnit)

			elif (g_recv_topic == '/req_weight'):
				#print("topic: ", g_recv_topic)
				weight = get_loadcell()
				#print(weight)
				dry_client.publish("/res_weight", weight)

			elif (g_recv_topic == '/print_lcd_internal_temp'):
				#print("topic: ", g_recv_topic)
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				top, bottom = json_to_val(data)
				#print ('print_lcd: ', top, ' ', bottom)
				displayTemp(top, bottom)

			elif (g_recv_topic == '/print_lcd_state'):
				#print("topic: ", g_recv_topic)
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				state = json_to_val(data)
				displayState(state)
				print('print_lcd_state')

			elif (g_recv_topic == '/print_lcd_debug_message'):
				#print("topic: ", g_recv_topic)
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				debug = json_to_val(data)
				#print (debug)
				displayMsg(debug)

			elif (g_recv_topic == '/print_lcd_loadcell'):
				#print("topic: ", g_recv_topic)
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				loadcell, target_loadcell = json_to_val(data)
				loadcell = str(loadcell)
				#print(loadcell, ' ', target_loadcell)
				target_loadcell = str(target_loadcell)
				#loadcell = (loadcell[2:(len(loadcell)-5)])
				#target_loadcell = (target_loadcell[2:(len(target_loadcell)-5)])
				displayLoadcell(loadcell, target_loadcell)

			elif (g_recv_topic == '/print_lcd_loadcell_factor'):
				#print("topic: ", g_recv_topic)
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				loadcell_factor, corr_val = json_to_val(data)
				displayLoadcellFactor(loadcell_factor)

			elif (g_recv_topic == '/print_lcd_input_door'):
				#print("topic: ", g_recv_topic)
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				input_door = json_to_val(data)
				displayInputDoor(input_door)

			elif (g_recv_topic == '/print_lcd_output_door'):
				#print("topic: ", g_recv_topic)
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				output_door = json_to_val(data)
				displayOutputDoor(output_door)
				print('print_lcd_output_door')

			elif (g_recv_topic == '/print_lcd_safe_door'):
				#print("topic: ", g_recv_topic)
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				val_safe_door = json_to_val(data)
				displaySafeDoor(val_safe_door)

			elif (g_recv_topic == '/print_lcd_elapsed_time'):
				#print("topic: ", g_recv_topic)
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				elapsed_time = json_to_val(data)
				elapsed_time = str(datetime.timedelta(seconds=elapsed_time))
				displayElapsed(elapsed_time)

	# 		elif (g_recv_topic == '/set_solenoid'):
	# 			#print("topic: ", g_recv_topic)
	# 			data = recv_msg.payload.decode('utf-8').replace("'", '"')
	# 			solenoid_val = json_to_val(data)
	# 			solenoid(Sol_val, solenoid_val)
	#
	# 		elif (g_recv_topic == '/set_fan'):
	# 			#print("topic: ", g_recv_topic)
	# 			data = recv_msg.payload.decode('utf-8').replace("'", '"')
	# 			fan_val = json_to_val(data)
	# 			fan(Cooling_motor, fan_val)
	#
	# 		elif (g_recv_topic == '/set_heater'):
	# 			#print("topic: ", g_recv_topic)
	# 			data = recv_msg.payload.decode('utf-8').replace("'", '"')
	# 			heat_val, heat_val2, heat_val3 = json_to_val(data)
	# 			heater(Heat_12, Heat_3, Heat_4, heat_val, heat_val2, heat_val3)
	#
	# 		elif (g_recv_topic == '/set_stirrer'):
	# 			#print("topic: ", g_recv_topic)
	# 			data = recv_msg.payload.decode('utf-8').replace("'", '"')
	# 			stirrer_val = json_to_val(data)
	# 			stirrer(Mix_motor, stirrer_val)

			elif (g_recv_topic == '/set_buzzer'):
				#print("topic: ", g_recv_topic)
				buzzer_running = 1
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				buzzer_val = json_to_val(data)
				buzzer(Buzzer, buzzer_val)
				buzzer_running = 0

			elif (g_recv_topic == '/set_zero_point'):
				#print("topic: ", g_recv_topic)
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				set_ref_Unit, set_corr_val = json_to_val(data)
				#print('set_zero_point - ',set_ref_Unit, ', ', set_corr_val)
				set_ref_Unit = float(set_ref_Unit)
				correlation_value = float(set_corr_val)
				set_factor(set_ref_Unit)
		except Empty:
			continue
		q.task_done()

t1 = threading.Thread(target=mqtt_dequeue)
t1.start()

period = 10000
while_count = 0
while True:
	while_count = while_count + 1
	if ((while_count % period) == 0):
		deb = debug_mode(Debug_switch_pin)
		dry_client.publish("/res_debug_mode", deb)

	if ((while_count % period) == 0):
		#print("topic: ", msg.topic)
		sw4_json = start_btn(SW4_pin)
		dry_client.publish("/res_start_btn", sw4_json)

	if ((while_count % period) == 0):
		#print("topic: ", msg.topic)
		json_input_door = get_input_door(Input_Door_pin)
		#print('input door: ', json_input_door)
		dry_client.publish("/res_input_door", json_input_door)

	if ((while_count % period) == 0):
		#print("topic: ", msg.topic)
		json_output_door = get_output_door(Output_Door_pin)
		#print("output door: ", json_output_door)
		dry_client.publish("/res_output_door", json_output_door)

	if ((while_count % period) == 0):
		#print("topic: ", msg.topic)
		json_safe_door = get_safe_door(Safe_Door_pin)
		#print("safe door: ", json_safe_door)
		dry_client.publish("/res_safe_door", json_safe_door)

	if ((while_count % period) == 0):
		#print("topic: ", msg.topic)
		json_operation_mode = Operation(Select_SW)
		#print("operation: ", json_operation_mode)
		dry_client.publish("/res_operation_mode", json_operation_mode)

# 	if (g_print_lcd_output_door_topic == '/print_lcd_output_door'):
# 		output_door = json_to_val(g_print_lcd_output_door_msg)
# 		displayOutputDoor(output_door)
# 		print('print_lcd_output_door')
# 		g_print_lcd_output_door_topic = ''
#
# 	elif (g_print_lcd_safe_door_topic == '/print_lcd_safe_door'):
# 		val_safe_door = json_to_val(g_print_lcd_safe_door_msg)
# 		displaySafeDoor(val_safe_door)
# 		print('print_lcd_safe_door')
# 		g_print_lcd_safe_door_topic = ''

	#g_lcd.backlight = True


