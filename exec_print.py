import sys, os, time, json, queue
import datetime
import board, busio
import paho.mqtt.client as mqtt
import adafruit_character_lcd.character_lcd_i2c as character_lcd

q = queue.Queue()

#---SET Pin-------------------------------------------------------------
# LCD I2C 
SDA = 30 # SDA_LCD-DAT 28
SCL = 31 # SCL_LCD-CLK 27

#---Parse Data----------------------------------------------------------
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
	q.put_nowait(f_msg)


def on_message(client, userdata, _msg):
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

dry_client.loop_start()

def mqtt_dequeue():
	if not q.empty():
		try:
			recv_msg = q.get(False)
			g_recv_topic = recv_msg.topic
			print(g_recv_topic)

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
				print('print_lcd_debug_message')

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

		except queue.Empty:
			pass
		q.task_done()

def core_func():
	period = 10000
	while_count = 0
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

	mqtt_dequeue()


if __name__ == "__main__":
	core_func()
