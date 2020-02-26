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

# Switch
SW2 = 35
SW3 = 39
SW4 = 41
SW5 = 16 # Debug Switch

# Load Cell
DAT = 6
CLK = 7

# LCD I2C
SDA = 30
SCL = 31

# Digital IN
DI15 = 11 # temperature & humidity

# Digital OUT
Buzzer = 17 	# Buzzer
DO9 = 40 	# LED Green
DO11 = 38	# LED Yellow
DO13 = 34	# LED Red
DO15 = 10	# LED module

state0 = 1
state1 = 1
state2 = 1

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(SW2, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(SW3, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(SW4, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(SW5, GPIO.IN, GPIO.PUD_UP)

GPIO.setup(Buzzer, GPIO.OUT)
GPIO.setup(DO9, GPIO.OUT)
GPIO.setup(DO11, GPIO.OUT)
GPIO.setup(DO13, GPIO.OUT)
GPIO.setup(DO15, GPIO.OUT) 


def json_to_val(json_val):
	payloadData = json.loads(json_val)
	val = payloadData['val']
	
	return (val)
	
	
def val_to_json(val):
	json_val = {"val":val}
	json_val = json.dumps(json_val)
	
	return (json_val)
	
	
def mqtt_connect(broker_address, port):
	dry_client = mqtt.Client()
	dry_client.on_connect = on_connect
	dry_client.on_disconnect = on_disconnect
	dry_client.on_subscribe = on_subscribe
	dry_client.on_message = on_message
	dry_client.connect(broker_address, port)
#	dry_client.subscribe("/print_lcd_internal_temp")
#	dry_client.subscribe("/print_lcd_state")
#	dry_client.subscribe("/print_lcd_debug_message")
	dry_client.subscribe("/print_lcd_loadcell")
#	dry_client.subscribe("/print_lcd_loadcell_factor")
#	dry_client.subscribe("/print_lcd_elapsed_time")
#	dry_client.subscribe("/print_lcd_input_door")
#	dry_client.subscribe("/print_lcd_output_door")
#	dry_client.subscribe("/print_lcd_safe_door")
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
#	dry_client.subscribe("/set_solenoid")
#	dry_client.subscribe("/set_fan")
#	dry_client.subscribe("/set_heater")
#	dry_client.subscribe("/set_stirrer")
#	dry_client.subscribe("/set_buzzer")


	dry_client.loop_start()
#	dry_client.loop_forever()

	return dry_client


def lcd_init():
	lcd_columns = 20
	lcd_rows = 4

	i2c = busio.I2C(board.SCL, board.SDA)

	lcd = character_lcd.Character_LCD_I2C(i2c, lcd_columns, lcd_rows)
	lcd.backlight = True

	return lcd
	
	
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
	

def displayMsg(msg, x, y):
	g_lcd.cursor_position(x,y)
	message = '     '
	g_lcd.message = message
	g_lcd.cursor_position(x,y)
	g_lcd.message = msg


def displayState(msg):
	if (msg == 'debug'):
		g_lcd.clear()
	g_lcd.cursor_position(0,0)
	message = '     '
	g_lcd.message = message
	g_lcd.cursor_position(0,0)
	g_lcd.message = msg


def temp_humi(DHT_PIN):
	#DHT_SENSOR = Adafruit_DHT.DHT22
	#humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
	#temperature = round(temperature, 1)
	
	#temp = val_to_json(temperature)
	#print("temperature: ", temperature)

	for i in range(5000):
		temperature = random.randint(25,30)
	temp = val_to_json(temperature)

	return (temp)
	
	
def debug_mode():
	debug_val = GPIO.input(16)
	debug_val = val_to_json(debug_val)

	return (debug_val)
	

def ref_weight(tare_weight):
	tare_weight = val_to_json(tare_weight)

	return (tare_weight)


def init_loadcell():
	# referenceUnit = 1571

	hx = HX711(6, 7)  # sparrow board pin. hx = HX711(DAT,CLK)
	hx.set_reading_format("MSB", "MSB")
	hx.set_reference_unit(1517)
	hx.reset()
	hx.tare()
	
	return hx
	

def calc_ref_Unit(hx, tare_weight):
	tare_weight = json_to_val(tare_weight)
	print("Add weight for initialize...")
	time.sleep(1)
	total = 0
	
	for i in range(5):	
		weight = hx.get_weight(5)
		print(weight)
		total += weight

	hx.power_down()
	hx.power_up()
			
	referenceUnit = ((total / (i+1)) / tare_weight)
	referenceUnit = val_to_json(referenceUnit)

	print("Remove weight for initialize...")
	time.sleep(1)
	hx.set_reference_unit(referenceUnit)
	hx.reset()
	hx.tare()
	print("Tare done! Add weight now...")
	referenceUnit = val_to_json(referenceUnit)

	return (hx, referenceUnit)


def cleanAndExit():
	print("Cleaning...")

	if not EMULATE_HX711:
		GPIO.cleanup()
		
	print("Bye!")
	sys.exit()


def get_loadcell(hx):
	try:
		weight = hx.get_weight(5)
		weight = round((weight/1000), 1)
#		print("Weight : ", weight/1000, " kg")
		weight = val_to_json(weight)

		hx.power_down()
		hx.power_up()

	except (KeyboardInterrupt, SystemExit):
		cleanAndExit()

	return (weight)

	
def DO_test(DO):
	print ("LED on" )
	GPIO.output(DO, GPIO.HIGH) 
	time.sleep(0.5)

	print ("LED off" )
	GPIO.output(DO, GPIO.LOW)
	time.sleep(0.5)
	
	
def switch():
	SW4 = GPIO.input(41)
	SW4 = val_to_json(SW4)
		
	return (SW4)
	
	
def buzzer(val):
	GPIO.output(17, val)
	print ("Beep")	
		

global dry_client
broker_address = "localhost"
port = 1883

global g_lcd
g_lcd = lcd_init()
dry_client = mqtt_connect(broker_address, port)

loadcell_ref_weight = 300

global hx
hx = init_loadcell()

while True:
	if(q.qsize()):
		msg = q.get()
		g_recv_topic = msg.topic;
		#print(g_recv_topic)
		if (g_recv_topic == '/req_internal_temp'):
			#print("topic: ", g_recv_topic)
			temperature = temp_humi(DI15)
			dry_client.publish("/res_internal_temp", temperature)
			
		elif (g_recv_topic == '/req_debug_mode'):
			#print("topic: ", g_recv_topic)
			deb = debug_mode()
			dry_client.publish("/res_debug_mode", deb)
			
		elif (g_recv_topic == '/req_start_btn'):
			#print("topic: ", g_recv_topic)
			sw4_json = switch()
			dry_client.publish("/res_start_btn", sw4_json)	


		elif (g_recv_topic == '/req_zero_point'):
			#print("topic: ", g_recv_topic)
			reference_weight = ref_weight(loadcell_ref_weight)
			dry_client.publish("/res_zero_point", reference_weight)
			
		elif (g_recv_topic == '/req_calc_factor'):
			#print("topic: ", g_recv_topic)
			hx, calc_referenceUnit = calc_ref_Unit(hx, reference_weight)
			dry_client.publish("/res_calc_factor", calc_referenceUnit)	
			
		elif (g_recv_topic == '/req_weight'):
			#print("topic: ", g_recv_topic)
			weight = get_loadcell(hx)
			dry_client.publish("/res_weight", weight)
			
		elif (g_recv_topic == '/req_input_door'):
			#print("topic: ", g_recv_topic)
			a = 8
			#dry_client.publish("/res_input_door", weight)
			
		elif (g_recv_topic == '/req_output_door'):
			#print("topic: ", g_recv_topic)
			a = 7
			#dry_client.publish("/res_output_door", weight)		
			
		elif (g_recv_topic == '/req_safe_door'):
			#print("topic: ", g_recv_topic)
			a = 6
			#dry_client.publish("/res_safe_door", weight)
					
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
			displayMsg(loadcell,0,1)

		elif (g_recv_topic == '/print_lcd_loadcell_factor'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			loadcell_factor = json_to_val(data)
			displayMsg(loadcell_factor,15,1)
			
		elif (g_recv_topic == '/print_lcd_input_door'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			input_door = json_to_val(data)
			displayMsg(input_door,0,2)
			
		elif (g_recv_topic == '/print_lcd_output_door'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			output_door = json_to_val(data)
			displayMsg(output_door,6,2)
			
		elif (g_recv_topic == '/print_lcd_safe_door'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			safe_door = json_to_val(data)
			displayMsg(safe_door,13,2)
			
		elif (g_recv_topic == '/print_lcd_elapsed_time'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			elapsed_time = json_to_val(data)
			displayMsg(elapsed_time,6,0)
						
		elif (g_recv_topic == '/set_solenoid'):
			#print("topic: ", g_recv_topic)
			a=2
			
		elif (g_recv_topic == '/set_fan'):
			#print("topic: ", g_recv_topic)
			a=3
			
		elif (g_recv_topic == '/set_heater'):
			#print("topic: ", g_recv_topic)
			a=4 
			
		elif (g_recv_topic == '/set_stirrer'):
			#print("topic: ", g_recv_topic)
			a=5 
			
		elif (g_recv_topic == '/set_buzzer'):
			#print("topic: ", g_recv_topic)
			data = msg.payload.decode('utf-8').replace("'", '"')
			Buzzer = json_to_val(data)
			buzzer(Buzzer)
