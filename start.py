"""Simple test for 16x2 character lcd connected to an MCP23008 I2C LCD backpack."""
import time
import board
import busio
import adafruit_character_lcd.character_lcd_i2c as character_lcd
import socket

# LCD I2C (Arduino)
SDA = 30
SCL = 31

def lcd_init():
	lcd_columns = 20
	lcd_rows = 4

	i2c = busio.I2C(board.SCL, board.SDA)

	lcd = character_lcd.Character_LCD_I2C(i2c, lcd_columns, lcd_rows)
	lcd.backlight = True

	return lcd
		

def displayMsg(msg, x, y):
	try:
		g_lcd.cursor_position(x,y)
		#print(msg)
		if (y == 3):
			message = '                    '
		else:
			message = ''
		g_lcd.message = message
		g_lcd.cursor_position(x,y)
		g_lcd.message = f'{msg}'
	
	except OSError:
		lcd_init()
		g_lcd.cursor_position(x,y)
		#print(msg)
		if (y == 3):
			message = '                    '
		else:
			message = ''
		g_lcd.message = message
		g_lcd.cursor_position(x,y)
		g_lcd.message = f'{msg}'
        
        
def get_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 0))
    ip = s.getsockname()[0]
    
    return ip
    
    
global g_lcd
g_lcd = lcd_init()
g_lcd.clear()

msg1 = 'Start Food Dryer'
displayMsg(msg1, 0, 1)

ip = get_address()
msg2 = 'IP: {}'.format(ip)
displayMsg(msg2, 0, 2)
