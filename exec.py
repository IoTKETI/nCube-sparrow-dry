import time
import board
import busio
import adafruit_character_lcd.character_lcd_i2c as character_lcd
import sys,json,numpy as np
import RPi.GPIO as GPIO
import Adafruit_DHT
import json
import paho.mqtt.client as mqtt



# Switch
SW2 = 35
SW3 = 39
SW4 = 41

# Load Cell
DAT = 6
CLK = 7

# LCD I2C
SDA = 30
SCL = 31

# Digital IN
DI15 = 11 # temperature & humidity

# Digital OUT
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

GPIO.setup(DO9, GPIO.OUT)
GPIO.setup(DO11, GPIO.OUT)
GPIO.setup(DO13, GPIO.OUT)
GPIO.setup(DO15, GPIO.OUT) 
	
def mqtt_connect(broker_address, port):
	dry_client = mqtt.Client()
	dry_client.on_connect = on_connect
	dry_client.on_disconnect = on_disconnect
	dry_client.on_subscribe = on_subscribe
	dry_client.on_message = on_message
	dry_client.connect(broker_address, port)
	dry_client.subscribe("/print_lcd_internal_temp")
	dry_client.subscribe("/print_lcd_state")

	for idx in topic:
		if idx in topic:
			idx = topic.index(idx)
			dry_client.subscribe(str(topic[idx]));
			print('[mqtt_connect] topic[' , idx , ']: ', topic[idx]);

	dry_client.loop_start()

	return dry_client

def lcd_init():
	lcd_columns = 20
	lcd_rows = 4

	i2c = busio.I2C(board.SCL, board.SDA)

	lcd = character_lcd.Character_LCD_I2C(i2c, lcd_columns, lcd_rows)
	lcd.backlight = True

	print (lcd)

	return lcd
	
	
def on_connect(client,userdata,flags, rc):
	print('[dry_mqtt_connect] connect to ', broker_address)


def on_disconnect(client, userdata, flags, rc=0):
	print(str(rc))


def on_subscribe(client, userdata, mid, granted_qos):
	print("subscribed: " + str(mid) + " " + str(granted_qos))


def on_message(client, userdata, msg):
	if (msg.topic == '/print_lcd_internal_temp'):
		print("topic: ", msg.topic)
		data = msg.payload.decode('utf-8').replace("'", '"')
		payloadData = json.loads(data)
		temper = payloadData['val']
		print ("pre_temp_msg: ", pre_temp_msg, "temper: ", temper)
		if (pre_temp_msg != temper):
			pre_temp_msg = temper
			displayTemp(temper)    
	elif (msg.topic == '/print_lcd_state'):
		print("topic: ", msg.topic)
		data = msg.payload.decode('utf-8').replace("'", '"')
		payloadData = json.loads(data)
		state = payloadData['val']
		print ("pre_state_msg: ", pre_state_msg, "state: ", state)
		if (pre_state_msg != state):
			pre_state_msg = state
			displayState(state)


def on_receive_from_msw(topic, str_message):
	print('[' + topic + '] ' + str_message)


def displayTemp(msg):
		g_lcd.cursor_position(15,0)
		message = '     '
		g_lcd.message = message
		g_lcd.cursor_position(15,0)
		g_lcd.message = f'{msg}'


def displayState(msg):
	g_lcd.cursor_position(0,0)
	message = '     '
	g_lcd.message = message
	g_lcd.cursor_position(0,0)
	g_lcd.message = msg


def init_loadcell(DAT, CLK, tare_weight):
	EMULATE_HX711=False

	# referenceUnit = 1571

	if not EMULATE_HX711:
		import RPi.GPIO as GPIO
		from hx711 import HX711
	else:
		from emulated_hx711 import HX711

	hx = HX711(DAT, CLK)  # sparrow board pin. hx = HX711(DAT,CLK)
	hx.set_reading_format("MSB", "MSB")
	hx.set_reference_unit(1)
	hx.reset()
	hx.tare()

	print("Add weight for initialize...")
	time.sleep(5)
	total = 0
	i = 0
	for i in range(5):
		print (i+1)
		weight = max(0, float(hx.get_weight(5)))
		print(weight)

	hx.power_down()
	hx.power_up()
	total += weight
			
	referenceUnit = ((total / (i+1))/tare_weight)
	print("referenceUnit : ",referenceUnit)
	print("Remove weight for initialize...")
	time.sleep(5)	
	hx.set_reference_unit(referenceUnit)
	hx.reset()
	hx.tare()
	print("Tare done! Add weight now...")

	return hx


def cleanAndExit():
	print("Cleaning...")

	if not EMULATE_HX711:
		GPIO.cleanup()
		
	print("Bye!")
	sys.exit()


def get_loadcell(hx):
	try:
		weight = max(0, float(hx.get_weight(5)))
		print("Weight : ", round((weight/1000), 1), " kg")

		hx.power_down()
		hx.power_up()

	except (KeyboardInterrupt, SystemExit):
		cleanAndExit()

	return (round((weight/1000), 1))

	
def temp_humi(DHT_PIN):
	DHT_SENSOR = Adafruit_DHT.DHT22
	humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
	temperature = round(temperature, 1)
	humidity = round(humidity, 1)

	if humidity is not None and temperature is not None:
		temp = {"val":temperature}
		temp = json.dumps(temp)
		#dry_client.publish("/get_internal_temp", temp)
		print("temperature: ", temperature)

	else:
		print("Failed to retrieve data from humidity sensor")

	return (temp, humidity)


def DO_test(DO):
	print ("LED on" )
	GPIO.output(DO, GPIO.HIGH) 
	time.sleep(0.5)

	print ("LED off" )
	GPIO.output(DO, GPIO.LOW)
	time.sleep(0.5)

######
#Test#
######

def main():

	global dry_client
	broker_address = "203.253.128.161"
	port = 1883
	global topic
	topic = ['/print_lcd_internal_temp']

	global g_lcd
	g_lcd = lcd_init()
	dry_client = mqtt_connect(broker_address, port)


	global hx
	#hx = init_loadcell(DAT,CLK, 600)
	while True:
		#weight = get_loadcell(hx)
		temperature, humidity = temp_humi(DI15)
		dry_client.publish("/get_internal_temp", temperature)
		#temp1 = temperature
		#temp2 = humidity
		#displayMsg(g_lcd)
		#DO_test(DO15)
		time.sleep(0.5)
		
if __name__ == '__main__':
	main()
