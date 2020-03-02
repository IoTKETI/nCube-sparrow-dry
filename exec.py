import time
import board
import busio
import adafruit_character_lcd.character_lcd_i2c as character_lcd
import sys,json,numpy as np
import RPi.GPIO as GPIO
import Adafruit_DHT
import json
import paho.mqtt.client as mqtt
from hx711 import HX711
from threading import Thread
import random
import queue

q = queue.Queue()

#---SET Pin-------------------------------------------------------------
# Switch
Debug_switch_pin = 16 # Debug Switch : Digital_Input_3
SW4_pin = 17 # Start Button : Digital_Input_4
Push_SW_pin = 26

# Load Cell vffffffffffffffffffffffffffffffff
DAT = 6
CLK = 7

# LCD I2C
SDA = 30
SCL = 31

# Digital IN
Input_Door_pin = 38 # Input Door Sensor() : Digital_Input_5
Output_Door_pin = 39 # Output Door Sensor() : Digital_Input_6
Safe_Door_pin = 40 # Safe Door Sensor(Front Door) : Digital_Input_7

# Digital OUT
Mix_motor = 34 # Digital_Output_13(red)
Cooling_motor = 35 # Digital_Output_14
Sol_val = 11 # Digital_Output_15
Heat_12 = 10 # Digital_Output_12
Heat_3 = 41 # Digital_Output_11
Heat_4 = 27 # Digital_Output_10

#---SET GPIO------------------------------------------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
# Switch
GPIO.setup(Debug_switch_pin, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(SW4_pin, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(Push_SW_pin, GPIO.IN, GPIO.PUD_UP)
# Door
GPIO.setup(Input_Door_pin, GPIO.IN,GPIO.PUD_UP)
GPIO.setup(Output_Door_pin, GPIO.IN,GPIO.PUD_UP)
GPIO.setup(Safe_Door_pin, GPIO.IN,GPIO.PUD_UP)
# Heater
GPIO.setup(Heat_12, GPIO.OUT)
GPIO.setup(Heat_3, GPIO.OUT)
GPIO.setup(Heat_4, GPIO.OUT)
# ETC
GPIO.setup(Sol_val, GPIO.OUT)
GPIO.setup(Mix_motor, GPIO.OUT)
GPIO.setup(Cooling_motor, GPIO.OUT)
# Output OFF Setting...
GPIO.output(Sol_val, GPIO.LOW)
GPIO.output(Mix_motor, GPIO.LOW)
GPIO.output(Cooling_motor, GPIO.LOW)
GPIO.output(Heat_12, GPIO.LOW)
GPIO.output(Heat_3, GPIO.LOW)
GPIO.output(Heat_4, GPIO.LOW)

def json_to_val(json_val):
#	if (str(type(json_val)) == "<class 'int'>"):
#		json_val = str(json_val)
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
	
	
def val_to_json(val):
	json_val = {"val":val}
	json_val = json.dumps(json_val)
	
	return (json_val)
	
#---MQTT----------------------------------------------------------------
def mqtt_connect(broker_address, port):
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
#	dry_client.subscribe("/print_lcd_elapsed_time")
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
#	dry_client.subscribe("/req_operation_mode")
	dry_client.subscribe("/set_solenoid")
	dry_client.subscribe("/set_fan")
	dry_client.subscribe("/set_heater")
	dry_client.subscribe("/set_stirrer")
#	dry_client.subscribe("/set_buzzer")
	dry_client.subscribe("/set_zero_point")


	dry_client.loop_start()
#	dry_client.loop_forever()

	return dry_client
	
	
def on_connect(client,userdata,flags, rc):
	print('[dry_mqtt_connect] connect to ', broker_address)


def on_disconnect(client, userdata, flags, rc=0):
	print(str(rc))


def on_subscribe(client, userdata, mid, granted_qos):
	print("subscribed: " + str(mid) + " " + str(granted_qos))


def func_set_q(msg):
	q.put(msg)


def on_message(client, userdata, msg):
	func_set_q(msg)
#-----------------------------------------------------------------------

#---INIT LCD & Display Message------------------------------------------
def lcd_init():
	lcd_columns = 20
	lcd_rows = 4

	i2c = busio.I2C(board.SCL, board.SDA)

	lcd = character_lcd.Character_LCD_I2C(i2c, lcd_columns, lcd_rows)
	lcd.backlight = True

	return lcd
		

def displayMsg(msg, x, y):
	g_lcd.cursor_position(x,y)
	#print(msg)
	if (y == 3):
		message = '                    '
	else:
		message = '      '
	g_lcd.message = message
	g_lcd.cursor_position(x,y)
	g_lcd.message = f'{msg}'


def displayState(msg):
	if (msg == 'DEBUG'):
		g_lcd.clear()
	g_lcd.cursor_position(0,0)
	message = '     '
	g_lcd.message = message
	g_lcd.cursor_position(0,0)
	g_lcd.message = f'{msg}'
#-----------------------------------------------------------------------

#---GET Temperature-----------------------------------------------------
def get_temp():
	#DHT_SENSOR = Adafruit_DHT.DHT22
	#humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
	#temperature = round(temperature, 1)
	
	#temp = val_to_json(temperature)
	#print("temperature: ", temperature)

	for i in range(5000):
		temperature = random.randint(25,30)
	temp = val_to_json(temperature)

	return (temp)
	
#---Debug Button--------------------------------------------------------	
def debug_mode(Debug_switch_pin):
	debug_val = GPIO.input(Debug_switch_pin)
	#print('debug_val: ', debug_val)
	
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
	print('init_referenceUnit: ', referenceUnit)
	global hx
	global nWeightCount
	nWeightCount = 5
	
	hx = HX711(6, 7)
	hx.set_reading_format("MSB", "MSB")
	hx.set_reference_unit(referenceUnit)
	hx.reset()
	#hx.tare()
	#print("Tare done! Add weight now...")


def calc_ref_Unit(reference_weight, set_ref_Unit):
	#reference_weight = 0.6
	#reference_weight = round((reference_weight/1000), 1)
	print ('calc_reference_weight: ', reference_weight, 'kg')
	ref_weight_total = 0

	for i in range(nWeightCount):	
		weight = hx.get_weight(5)
		#weight = round((val/1000), 1)
		print(weight)
		ref_weight_total += weight
		
	avg_ref_weight = (ref_weight_total / nWeightCount)
	print ("avg_ref_weight: ", avg_ref_weight)
	cur_weight = (avg_ref_weight - avg_zero_weight)
	print ("cur_weight: ", cur_weight)
	cur_factor = (cur_weight / reference_weight)
	'''
	if (avg_zero_weight == 0 and cur_weight > reference_weight):
		cur_factor = cur_factor + set_ref_Unit
	elif (avg_zero_weight == 0 and cur_weight < reference_weight):
		cur_factor = cur_factor + set_ref_Unit
		'''
		
	if (cur_factor == 0.0):
		cur_factor = set_ref_Unit
	print("cur_factor: ", cur_factor)

	hx.set_reference_unit(cur_factor)
	hx.reset()

	print("Complete!")
        
	calc_ref_unit = val_to_json(cur_factor)

	return calc_ref_unit

# 208.2 - 311.0 = -102.8
# 227.77 - 208.2 = 19.57

def get_loadcell():
	global flag

	try:
		if (flag == 0):
			for i in range(nWeightCount):
				weight = hx.get_weight(5)
				#weight = round((val/1000), 1)
				weight_arr[i] = weight
				flag = 1
		else:
			weight = hx.get_weight(5)
			#weight = round((val/1000), 1)
			for i in range(nWeightCount):
				if (i > 0):
					weight_arr[i-1] = weight_arr[i]
				weight_arr[nWeightCount-1] = weight
				
		#print('weight_arr: ', weight_arr)
		avg_weight = round((sum(weight_arr) / nWeightCount), 2)
		loadcell_weight = avg_weight - reference_weight
		final_weight = avg_weight - loadcell_weight
		print('Load Cell Weight: ', final_weight)
		
		weight_json = val_to_json(final_weight)

	except (KeyboardInterrupt, SystemExit):
		cleanAndExit()
		
	except NameError:
		weight_json = val_to_json(0)

	return (weight_json)


def ref_weight(tare_weight):
	global reference_weight
	reference_weight = tare_weight
	
	val = val_to_json(1)
	
	init_loadcell(1)
	global avg_zero_weight
	zero_weight = 0
	for i in range(nWeightCount):	
		weight = hx.get_weight(5)
		#weight = round((val/1000), 1)
		#print(weight)
		zero_weight += weight

	avg_zero_weight = (zero_weight / nWeightCount)
	print ("avg_zero_weight: ", avg_zero_weight)
	# parameter detail setting for calibration
	
	print("Add weight for initialize...")
		
	return val
#-----------------------------------------------------------------------
	
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

#---Start Button--------------------------------------------------------		
def start_btn(SW4_pin):
	SW4 = GPIO.input(SW4_pin)
	#print('SW4: ', SW4)
	SW4 = val_to_json(SW4)
		
	return (SW4)
	
	
#---Buzzer--------------------------------------------------------------			
def buzzer(val):
	GPIO.output(17, val)
	print ("Beep")	

#---Heater--------------------------------------------------------------
def heater(Heat_12, Heat_3, Heat_4, val, val2, val3):
	GPIO.output(Heat_12, val)
	GPIO.output(Heat_3, val2)
	GPIO.output(Heat_4, val3)

#---Solenoid------------------------------------------------------------
def solenoid(Sol_val, val):
	GPIO.output(Sol_val, val)
	
#---Fan-----------------------------------------------------------------
def fan(Cooling_motor, val):
	GPIO.output(Cooling_motor, val)
	
#---Stirrer-------------------------------------------------------------
def stirrer(Mix_motor, val):
	GPIO.output(Mix_motor, val)

#=======================================================================
global dry_client
broker_address = "localhost"
port = 1883

global g_lcd
g_lcd = lcd_init()
dry_client = mqtt_connect(broker_address, port)

global set_ref_Unit
set_ref_Unit = 1
weight_arr = [0, 0, 0, 0, 0]
flag = 0

while True:
	if(q.qsize()):
		msg = q.get()
		g_recv_topic = msg.topic;
		#print(g_recv_topic)
		if (g_recv_topic == '/req_internal_temp'):
			#print("topic: ", g_recv_topic)
			temperature = get_temp()
			dry_client.publish("/res_internal_temp", temperature)
			
		elif (g_recv_topic == '/req_debug_mode'):
			#print("topic: ", g_recv_topic)
			deb = debug_mode(Debug_switch_pin)
			dry_client.publish("/res_debug_mode", deb)
			
		elif (g_recv_topic == '/req_start_btn'):
			#print("topic: ", g_recv_topic)
			sw4_json = start_btn(SW4_pin)
			dry_client.publish("/res_start_btn", sw4_json)	


		elif (g_recv_topic == '/req_zero_point'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
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
#			print(weight)
			dry_client.publish("/res_weight", weight)
			
		elif (g_recv_topic == '/req_input_door'):
			#print("topic: ", g_recv_topic)
			json_input_door = get_input_door(Input_Door_pin)
			dry_client.publish("/res_input_door", json_input_door)
			
		elif (g_recv_topic == '/req_output_door'):
			#print("topic: ", g_recv_topic)
			json_output_door = get_output_door(Output_Door_pin)
			dry_client.publish("/res_output_door", json_output_door)		
			
		elif (g_recv_topic == '/req_safe_door'):
			#print("topic: ", g_recv_topic)
			json_safe_door = get_safe_door(Safe_Door_pin)
			dry_client.publish("/res_safe_door", json_safe_door)
					
		elif (g_recv_topic == '/req_operation_mode'):
			#print("topic: ", g_recv_topic)
			a = 1
			#dry_client.publish("/res_operation_mode", weight)		
				
		elif (g_recv_topic == '/print_lcd_internal_temp'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			temper = json_to_val(data)
			displayMsg(temper, 15,0)    
			
		elif (g_recv_topic == '/print_lcd_state'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			state = json_to_val(data)
			displayState(state)
			
		elif (g_recv_topic == '/print_lcd_debug_message'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			debug = json_to_val(data)
			displayMsg(debug, 0, 3)
					
		elif (g_recv_topic == '/print_lcd_loadcell'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			loadcell = json_to_val(data)
			loadcell = str(loadcell)
			loadcell = (loadcell[2:(len(loadcell)-5)])
			displayMsg(loadcell,0,1)

		elif (g_recv_topic == '/print_lcd_loadcell_factor'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			loadcell_factor, corr_val = json_to_val(data)
			displayMsg(loadcell_factor,14,1)
			
		elif (g_recv_topic == '/print_lcd_input_door'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			input_door = json_to_val(data)
			displayMsg(input_door,1,2)
			
		elif (g_recv_topic == '/print_lcd_output_door'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			output_door = json_to_val(data)
			displayMsg(output_door,6,2)
			
		elif (g_recv_topic == '/print_lcd_safe_door'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			val_safe_door = json_to_val(data)
			displayMsg(val_safe_door,19,2)
			
		elif (g_recv_topic == '/print_lcd_elapsed_time'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			elapsed_time = json_to_val(data)
			displayMsg(elapsed_time,6,0)
						
		elif (g_recv_topic == '/set_solenoid'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			solenoid_val = json_to_val(data)
			solenoid(Sol_val, solenoid_val) 
						
		elif (g_recv_topic == '/set_fan'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			fan_val = json_to_val(data)
			fan(Cooling_motor, fan_val) 
						
		elif (g_recv_topic == '/set_heater'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			heat_val, heat_val2, heat_val3 = json_to_val(data)
			heater(Heat_12, Heat_3, Heat_4, heat_val, heat_val2, heat_val3) 
						
		elif (g_recv_topic == '/set_stirrer'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			stirrer_val = json_to_val(data)
			stirrer(Mix_motor, stirrer_val) 
			
		elif (g_recv_topic == '/set_buzzer'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			buzzer_val = json_to_val(data)
			buzzer(buzzer_val)
			
		elif (g_recv_topic == '/set_zero_point'):
			print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			set_ref_Unit, set_corr_val = json_to_val(data)
			print('set_zero_point - ',set_ref_Unit, ', ', set_corr_val)
			set_ref_Unit = float(set_ref_Unit)
			init_loadcell(set_ref_Unit)
