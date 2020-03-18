import sys, os, json, queue
import datetime
import board, busio
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import MAX6675
from hx711 import HX711

global g_print_lcd_output_door_topic
g_print_lcd_output_door_topic = ''

global g_print_lcd_output_door_msg
g_print_lcd_output_door_msg = ''

global g_print_lcd_safe_door_topic
g_print_lcd_safe_door_topic = ''

global g_print_lcd_safe_door_msg
g_print_lcd_safe_door_msg = ''

q = queue.Queue()
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

# Digital IN
Input_Door_pin = 7 # Input Door Sensor() : Digital_Input_4
Output_Door_pin = 10 # Output Door Sensor() : Digital_Input_5
Safe_Door_pin = 11 # Safe Door Sensor(Front Door) : Digital_Input_6

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
# Temperature
sensor1 = MAX6675.MAX6675(CLK1, CS1, SO1)
sensor2 = MAX6675.MAX6675(CLK2, CS2, SO2)
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
	print('set_factor: ', referenceUnit)
	hx.set_reference_unit(referenceUnit)
	hx.reset()
	

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
		final_weight = avg_weight - loadcell_corr_val
		final_weight = max(0, float(final_weight))
		# print('weight_arr: ', weight_arr)
		print('get_loadcell - correlation_value: ', loadcell_corr_val)
		print('get_loadcell - avg_weight: ', avg_weight)
		print('get_loadcell - final_weight: ', final_weight)
		weight_json = val_to_json(final_weight)

	except (KeyboardInterrupt, SystemExit):
		cleanAndExit()

	return (weight_json)


def ref_weight(tare_weight):
	global avg_zero_weight  

	val = val_to_json(1)

	init_loadcell(1)

	zero_weight = 0
	for i in range(5):
		weight = hx.get_weight(5)
		zero_weight += weight

	avg_zero_weight = (zero_weight / 5)
	avg_zero_weight = max(0, float(avg_zero_weight))

	print("Add weight for initialize...")

	return val
	

def calc_ref_Unit(reference_weight, cal_set_ref_Unit):   	
	print('calc_ref_Unit: ', reference_weight, ' ', cal_set_ref_Unit)

	ref_weight_total = 0

	for i in range(nWeightCount):
		weight = hx.get_weight(5)
		ref_weight_total += weight

	print('calc_ref_Unit - avg_zero_weight: ', avg_zero_weight)

	avg_ref_weight = (ref_weight_total / nWeightCount)
	cur_weight = (avg_ref_weight - avg_zero_weight)
	cur_weight = max(0, float(cur_weight))
	cur_factor = (cur_weight / reference_weight)
	print('calc_ref_Unit - cur_weight: ', cur_weight)
	print('calc_ref_Unit - cur_factor: ', cur_factor)

	if (cur_factor == 0.0):
		cur_factor = cal_set_ref_Unit

	hx.set_reference_unit(cur_factor)
	hx.reset()

	factor_weight_total = 0

	for i in range(nWeightCount):
		weight = hx.get_weight(5)
		factor_weight_total += weight

	avg_factor_weight = (factor_weight_total / nWeightCount)
	avg_factor_weight = max(0, float(avg_factor_weight))
	set_correlation_value = avg_factor_weight - reference_weight
	factor = {"factor":cur_factor, "correlation_value":set_correlation_value}
	print('calc_ref_Unit - avg_factor_weight: ', avg_factor_weight)
	print('calc_ref_Unit - correlation_value: ', set_correlation_value)
	with open ("./factor.json", "w") as factor_json:
		json.dump(factor, factor_json)

	print("Complete!")

	calc_ref_unit = val_to_json(cur_factor, set_correlation_value)

	return calc_ref_unit
#-----------------------------------------------------------------------

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

dry_client.subscribe("/req_internal_temp")
dry_client.subscribe("/req_weight")
dry_client.subscribe("/req_zero_point")
dry_client.subscribe("/req_calc_factor")
dry_client.subscribe("/set_zero_point")
# dry_client.subscribe("/req_debug_mode")
# dry_client.subscribe("/req_start_btn")
# dry_client.subscribe("/req_input_door")
# dry_client.subscribe("/req_output_door")
# dry_client.subscribe("/req_safe_door")
# dry_client.subscribe("/req_operation_mode")

dry_client.loop_start()

global loadcell_factor
global loadcell_corr_val

loadcell_param = {"factor":6555,"correlation_value":200}

if (os. path.isfile("./factor.json") == False):
	with open("./factor.json","w") as refUnit_json:
		json.dump(loadcell_param, refUnit_json)
	loadcell_factor = loadcell_param['factor']
	loadcell_corr_val = loadcell_param['correlation_value']
else:
	# with open ("./factor.json", "r") as refUnit_json:
	# 	loadcell_factor = json.load(refUnit_json)
	refUnit_json = open("./factor.json").read()
	data = json.loads(refUnit_json) 

	loadcell_factor = data['factor']
	loadcell_corr_val = data['correlation_value']
	# loadcell_corr_val = int(loadcell_corr_val)

init_loadcell(loadcell_factor)

weight_arr = [0, 0, 0, 0, 0]
flag = 0

# def mqtt_dequeue():
	# if not q.empty():
    # 		try:
	# 		recv_msg = q.get(False)
	# 		g_recv_topic = recv_msg.topic
	# 		print(g_recv_topic)

	# 		if (g_recv_topic == '/req_internal_temp'):
	# 			#print("topic: ", g_recv_topic)
	# 			temperature = get_temp()
	# 			dry_client.publish("/res_internal_temp", temperature)

	# 		elif (g_recv_topic == '/req_zero_point'):
	# 			#print("topic: ", g_recv_topic)
	# 			data = recv_msg.payload.decode('utf-8').replace("'", '"')
	# 			req_zero_reference_weight = json.loads(data)
	# 			req_zero_ref_weight = req_zero_reference_weight['val']
	# 			#print ("reference_weight: ", req_zero_reference_weight)
	# 			val = ref_weight(req_zero_ref_weight)
	# 			dry_client.publish("/res_zero_point", val)

	# 		elif (g_recv_topic == '/req_calc_factor'):
	# 			#print("topic: ", g_recv_topic)
	# 			calc_referenceUnit = calc_ref_Unit(req_zero_ref_weight, referenceUnit)
	# 			dry_client.publish("/res_calc_factor", calc_referenceUnit)

	# 		elif (g_recv_topic == '/req_weight'):
	# 			#print("topic: ", g_recv_topic)
	# 			# weight = get_loadcell(correlation_value)
	# 			weight = get_loadcell()
	# 			#print(weight)
	# 			dry_client.publish("/res_weight", weight)
			
	# 		elif (g_recv_topic == '/set_zero_point'):
	# 			#print("topic: ", g_recv_topic)
	# 			data = recv_msg.payload.decode('utf-8').replace("'", '"')
	# 			referenceUnit, set_corr_val = json_to_val(data)
	# 			referenceUnit = float(referenceUnit)
	# 			correlation_value = float(set_corr_val)
	# 			#print ('set_zero_point: ', referenceUnit, ' ', correlation_value)
	# 			set_factor(referenceUnit)

	# 	except queue.Empty:
	# 		pass
	# 	q.task_done()

def core_func():
	period = 10000
	while_count = 0
	global req_zero_ref_weight
	referenceUnit = 1
	correlation_value = 200

	while True:
		while_count = while_count + 1
		#print(while_count)
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
		
		# mqtt_dequeue()
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
					req_zero_reference_weight = json.loads(data)
					req_zero_ref_weight = req_zero_reference_weight['val']
					#print ("reference_weight: ", req_zero_reference_weight)
					val = ref_weight(req_zero_ref_weight)
					dry_client.publish("/res_zero_point", val)

				elif (g_recv_topic == '/req_calc_factor'):
					#print("topic: ", g_recv_topic)
					calc_referenceUnit = calc_ref_Unit(req_zero_ref_weight, referenceUnit)
					dry_client.publish("/res_calc_factor", calc_referenceUnit)

				elif (g_recv_topic == '/req_weight'):
					#print("topic: ", g_recv_topic)
					# weight = get_loadcell(correlation_value)
					weight = get_loadcell()
					#print(weight)
					dry_client.publish("/res_weight", weight)
				
				elif (g_recv_topic == '/set_zero_point'):
					#print("topic: ", g_recv_topic)
					data = recv_msg.payload.decode('utf-8').replace("'", '"')
					referenceUnit, set_corr_val = json_to_val(data)
					referenceUnit = float(referenceUnit)
					correlation_value = float(set_corr_val)
					#print ('set_zero_point: ', referenceUnit, ' ', correlation_value)
					set_factor(referenceUnit)

			except queue.Empty:
				pass
			q.task_done()

if __name__ == "__main__":
	core_func()