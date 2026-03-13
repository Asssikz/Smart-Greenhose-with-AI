'''
Actuators module for the project.
This module is responsible for controlling the actuators.
'''

from pibody import Servo, LEDTower, LED
from config import ACTUATORS_PIN
from InnerPico.telemetry import telemetry_data
from helpers import periodic, logger

try:
    fan_ch   = LED(ACTUATORS_PIN['FAN'])
    window_1 = Servo(ACTUATORS_PIN['WINDOW_1'])
    window_2 = Servo(ACTUATORS_PIN['WINDOW_2'])
    door     = Servo(ACTUATORS_PIN['DOOR'])
    pump     = LED(ACTUATORS_PIN['PUMP'])
    fan_led  = LEDTower(ACTUATORS_PIN['FAN_LED'])
    light    = LEDTower(ACTUATORS_PIN['LED_TOWER'], led_num=16)
except Exception as e:
    print(f"Error initializing actuators: {e}")

actuator_state = {
    'COOLER': None,
    'HEATER': None,
    'WINDOW_1': None,
    'WINDOW_2': None,
    'DOOR': None,
    'LIGHT': None,
    'PUMP': None
}

automation_state = {
    'COOLER': True,
    'HEATER': True,
    'WINDOWS': True,
    'DOOR': True,
    'LIGHT': True,
    'PUMP': True
}

automation_thresholds = {
    'TEMP_HIGH':   25.0,   # > 26°C → cooler on / < 26°C → cooler off
    'TEMP_LOW':    20.0,   # < 20°C → heater on / > 20°C → heater off
    'HUMID_HIGH':  50.0,   # > 50% → windows open
    'HUMID_LOW':   40.0,   # < 40% → windows close
    'LIGHT_HIGH':  0.4,    # < 0.4 → light on
    'LIGHT_LOW':   0.6,    # > 0.6 → light off
    'SOIL_HIGH':   0.5,    # > 0.5 → pump on
    'SOIL_LOW':    0.4,    # < 0.4 → pump off
}

def cooler_on():
    global automation_state, actuator_state
    actuator_state['COOLER'] = True
    automation_state['COOLER'] = False
    fan_led.fill(fan_led.CYAN)
    fan_led.write()
    fan_ch.on()

def cooler_off():
    global automation_state, actuator_state
    actuator_state['COOLER'] = False
    automation_state['COOLER'] = False
    if not automation_state['HEATER']:
        fan_led.fill(fan_led.BLACK)
        fan_led.write()
    fan_ch.off()

def heater_on():
    global automation_state, actuator_state
    actuator_state['HEATER'] = True
    automation_state['HEATER'] = False
    fan_led.fill(fan_led.RED)
    fan_led.write()
    fan_ch.on()

def heater_off():
    global automation_state, actuator_state
    actuator_state['HEATER'] = False
    automation_state['HEATER'] = False
    if not automation_state['COOLER']:
        fan_led.fill(fan_led.BLACK)
        fan_led.write()
    fan_ch.off()

def window_1_open():
    global automation_state, actuator_state
    actuator_state['WINDOW_1'] = True
    automation_state['WINDOWS'] = False
    window_1.angle(90)

def window_1_close():
    global automation_state, actuator_state
    actuator_state['WINDOW_1'] = False
    automation_state['WINDOWS'] = False
    window_1.angle(0)

def window_2_open():
    global automation_state, actuator_state
    actuator_state['WINDOW_2'] = True
    automation_state['WINDOWS'] = False
    window_2.angle(90)

def window_2_close():
    global automation_state, actuator_state
    actuator_state['WINDOW_2'] = False
    automation_state['WINDOWS'] = False
    window_2.angle(0)

def all_windows_open():
    window_1_open()
    window_2_open()

def all_windows_close():
    window_1_close()
    window_2_close()

def door_open():
    global automation_state, actuator_state
    actuator_state['DOOR'] = True
    automation_state['DOOR'] = False
    door.angle(0)

def door_close():
    global automation_state, actuator_state
    actuator_state['DOOR'] = False
    automation_state['DOOR'] = False
    door.angle(50)

def light_on():
    global automation_state, actuator_state
    actuator_state['LIGHT'] = True
    automation_state['LIGHT'] = False
    light.fill(light.WHITE)
    light.write()

def light_uv():
    global automation_state, actuator_state
    actuator_state['LIGHT'] = True
    automation_state['LIGHT'] = False
    light.fill(light.PURPLE)
    light.write()

def light_off():
    global automation_state, actuator_state
    actuator_state['LIGHT'] = False
    automation_state['LIGHT'] = False
    light.fill(light.BLACK)
    light.write()

def pump_on():
    global automation_state, actuator_state
    actuator_state['PUMP'] = True
    automation_state['PUMP'] = False
    pump.on()

def pump_off():
    global automation_state, actuator_state
    actuator_state['PUMP'] = False
    automation_state['PUMP'] = False
    pump.off()


def automation_on():
    global automation_state
    automation_state = {
        'COOLER': True,
        'HEATER': True,
        'WINDOWS': True,
        'DOOR': True,
        'LIGHT': True,
        'PUMP': True
    }
    return automation_state

def automation_off():
    global automation_state
    automation_state = {
        'COOLER': False,
        'HEATER': False,
        'WINDOWS': False,
        'DOOR': False,
        'LIGHT': False,
        'PUMP': False
    }
    return automation_state

@periodic(1)
def get_actuator_state(timer):
    global actuator_state
    actuator_state = {
        'COOLER': True if fan_led[0] == fan_led.CYAN else False,
        'HEATER': True if fan_led[0] == fan_led.RED else False,
        'WINDOW_1': True if window_1.angle() == 0 else False,
        'WINDOW_2': True if window_2.angle() == 0 else False,
        'DOOR': True if door.angle() == 90 else False,
        'LIGHT': True if light[0] != light.BLACK else False,
        'PUMP': True if pump.value() == 1 else False
    }
    return actuator_state

def automation_loop(timer):
    global automation_state, actuator_state
    # Cooler
    if automation_state['COOLER'] and telemetry_data['temp'] > automation_thresholds['TEMP_HIGH']:
        cooler_on()
        automation_state['COOLER'] = True
    elif automation_state['COOLER'] and telemetry_data['temp'] < automation_thresholds['TEMP_HIGH']:
        cooler_off()
        automation_state['COOLER'] = True

    # Heater
    if automation_state['HEATER'] and telemetry_data['temp'] < automation_thresholds['TEMP_LOW']:
        heater_on()
        automation_state['HEATER'] = True
    elif automation_state['HEATER'] and telemetry_data['temp'] > automation_thresholds['TEMP_LOW']:
        heater_off()
        automation_state['HEATER'] = True
    
    # Windows
    if automation_state['WINDOWS'] and telemetry_data['humidity'] > automation_thresholds['HUMID_HIGH']:
        all_windows_open()
        automation_state['WINDOWS'] = True
    elif automation_state['WINDOWS'] and telemetry_data['humidity'] < automation_thresholds['HUMID_LOW']:
        all_windows_close()
        automation_state['WINDOWS'] = True

    # Light
    if automation_state['LIGHT'] and telemetry_data['light'] < automation_thresholds['LIGHT_HIGH']:
        light_on()
        automation_state['LIGHT'] = True
    elif automation_state['LIGHT'] and telemetry_data['light'] > automation_thresholds['LIGHT_LOW']:
        light_off()
        automation_state['LIGHT'] = True

    # Pump
    if automation_state['PUMP'] and telemetry_data['soil_moisture'] < automation_thresholds['SOIL_LOW']:
        pump_on()   
        automation_state['PUMP'] = True
    elif automation_state['PUMP'] and telemetry_data['soil_moisture'] > automation_thresholds['SOIL_HIGH']:
        pump_off()
        automation_state['PUMP'] = True

    # Door
    if automation_state['DOOR'] and telemetry_data['motion'] == 1:
        door_open()
        automation_state['DOOR'] = True
    elif automation_state['DOOR'] and telemetry_data['motion'] == 0:
        door_close()
        automation_state['DOOR'] = True
