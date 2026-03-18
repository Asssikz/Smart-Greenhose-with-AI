'''
Telemetry module for the project.
This module is responsible for collecting and storing telemetry data from the modules.
The data is stored in a JSON file.
'''

from pibody import Climate, ADC, Motion
from config import SENSORS_PIN
from helpers import periodic, logger

# ── INITIALIZATION ────────────────────────────────────────────────────────────
try:
    climate         = Climate(SENSORS_PIN['CLIMATE'])
    light_sensor    = ADC(SENSORS_PIN['LIGHT'])
    soil_moisture   = ADC(SENSORS_PIN['SOIL_MOISTURE'])
    motion_sensor   = Motion(SENSORS_PIN['MOTION'])
except Exception as e:
    print(f"Error initializing telemetry: {e}")
    climate         = None

telemetry_data = {
    "temp": None,
    "humidity": None,
    "light": None,
    "soil_moisture": None,
    "motion": None
}

@periodic(freq=4)
def telemetry_measurement(timer):
    global telemetry_data
    telemetry_data["temp"]          = round(climate.read_temperature(), 1) if climate is not None else 0
    telemetry_data["humidity"]      = round(climate.read_humidity(), 1) if climate is not None else 0
    telemetry_data["light"]         = round(light_sensor.read(), 2)
    telemetry_data["soil_moisture"] = round(soil_moisture.read(), 2)
    telemetry_data["motion"]        = motion_sensor.read()
    return telemetry_data