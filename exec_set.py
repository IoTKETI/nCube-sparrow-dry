import json, queue
import serial
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

q = queue.Queue()

#---SET Pin-------------------------------------------------------------
# Digital OUT (Arduino)
Heat_12 = 13 # Digital_Output_12
Heat_3 = 12 # Digital_Output_11
Heat_4 = 11 # Digital_Output_10
Mix_motor = 10 # Digital_Output_13(red)
Cooling_motor = 9 # Digital_Output_14
Sol_val = 6 # Digital_Output_15
Buzzer = 5

# #---Serial Communication with Arduino-----------------------------------
# def Serial_Feather(pin=None, pin2=None, pin3=None, val=None, val2=None, val3=None):
# 	if (pin != None and pin2 == None and pin3 == None):
# 		ser_msg = ('<' + str(pin) + ',' + str(val) + '>\n').encode()
# 		#print(ser_msg)
# 		ser.write(ser_msg)
# 	elif (pin != None and pin2 != None and pin3 != None):
# 		ser_msg = ('<' + str(pin) + ',' + str(val) + '/' + str(pin2) + ',' + str(val2) + '/' + str(pin3) + ',' + str(val3) + '>\n').encode()
# 		#print(ser_msg)
# 		ser.write(ser_msg)
# #-----------------------------------------------------------------------

#---Heater--------------------------------------------------------------
def heater(val, val2, val3):
	# Serial_Feather(pin=Heat_12, pin2=Heat_3, pin3=Heat_4, val=val, val2=val2, val3=val3)
	heater12_msg = (':' + 'HA' + '/' + str(val) + ';').encode()
	heater3_msg = (':' + 'HB' + '/' + str(val2) + ';').encode() 
	heater4_msg = (':' + 'HC' + '/' + str(val3) + ';').encode()
	ser.write(heater12_msg)
	ser.write(heater3_msg)
	ser.write(heater4_msg)

#---Stirrer-------------------------------------------------------------
def stirrer(val):
	# Serial_Feather(pin=Mix_motor, val=val)
	stirrer_msg = (':' + 'SA' + '/' + str(val) + ';').encode()
	ser.write(stirrer_msg)

#---Fan-----------------------------------------------------------------
def fan(val):
	# Serial_Feather(pin=Cooling_motor, val=val)
	fan_msg = (':' + 'FA' + '/' + str(val) + ';').encode()
	ser.write(fan_msg)

#---Solenoid------------------------------------------------------------
def solenoid(val):
	#Serial_Feather(pin=Sol_val, val=val)
	solenoid_msg = (':' + 'SV' + '/' + str(val) + ';').encode()
	ser.write(solenoid_msg)

#---Buzzer--------------------------------------------------------------
def buzzer(val):
	#Serial_Feather(pin=Buzzer, val=val)
	buzzer_msg = (':' + 'BZ' + '/' + str(val + ';')).encode()
	ser.write(buzzer_msg)

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
	# if(f_msg.topic == '/set_buzzer'):
	# 	if(buzzer_running == 0):
	# 		q.put_nowait(f_msg)

	if (f_msg.topic == '/set_solenoid'):
		#print("topic: ", f_msg.topic)
		data = f_msg.payload.decode('utf-8').replace("'", '"')
		solenoid_val = json_to_val(data)
		solenoid(solenoid_val)

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

	else: 
		q.put_nowait(f_msg)


def on_message(client, userdata, _msg):
	func_set_q(_msg)
#-----------------------------------------------------------------------

#=======================================================================
global dry_client
broker_address = "localhost"
port = 1883

dry_client = mqtt.Client()
dry_client.on_connect = on_connect
dry_client.on_disconnect = on_disconnect
dry_client.on_subscribe = on_subscribe
dry_client.on_message = on_message
dry_client.connect(broker_address, port)

dry_client.subscribe("/set_solenoid")
dry_client.subscribe("/set_fan")
dry_client.subscribe("/set_heater")
dry_client.subscribe("/set_stirrer")
dry_client.subscribe("/set_buzzer")

dry_client.loop_start()



def mqtt_dequeue():
	if not q.empty():
		try:
			recv_msg = q.get(False)
			g_recv_topic = recv_msg.topic
			print(g_recv_topic)

			if (g_recv_topic == '/set_buzzer'):
				#print("topic: ", g_recv_topic)
				buzzer_running = 1
				data = recv_msg.payload.decode('utf-8').replace("'", '"')
				buzzer_val = json_to_val(data)
				buzzer(Buzzer, buzzer_val)
				buzzer_running = 0

		except queue.Empty:
			pass
		q.task_done()

def core_func():
	period = 10000
	while_count = 0
	while True:
		while_count = while_count + 1
		mqtt_dequeue()

if __name__ == "__main__":
	global ser
	ser = serial.Serial("/dev/ttyAMA0", 9600)
	core_func()
