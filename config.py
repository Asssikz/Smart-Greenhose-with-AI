'''
All configuration for the project.
'''

## ─ Outer PiBody Configuration ────────────────────────────────────────────────
# ── MicroSD ───────────────────────────────────────────────────────────────────
MicroSD_CS               = 17
MicroSD_SCK              = 18
MicroSD_MOSI             = 19
MicroSD_MISO             = 16

MicroSD_CONFIG = {
    'cs': MicroSD_CS, 
    'sck': MicroSD_SCK, 
    'mosi': MicroSD_MOSI, 
    'miso': MicroSD_MISO}
# ── MicroSD ───────────────────────────────────────────────────────────────────
# ── I2S and Audio CONFIGURATION ───────────────────────────────────────────────
SCK_PIN                  = 0
WS_PIN                   = 1
SD_PIN                   = 2
I2S_ID                   = 0
BUFFER_LENGTH_IN_BYTES   = 16000

WAV_SAMPLE_SIZE_IN_BITS  = 16
SAMPLE_RATE_IN_HZ        = 16000
NUM_CHANNELS             = 1
WAV_SAMPLE_SIZE_IN_BYTES = WAV_SAMPLE_SIZE_IN_BITS // 8

I2S_CONFIG = {
    'sck': SCK_PIN, 
    'ws': WS_PIN, 
    'sd': SD_PIN, 
    'id': I2S_ID, 
    'buffer_length': BUFFER_LENGTH_IN_BYTES,
    'bits': WAV_SAMPLE_SIZE_IN_BITS, 
    'rate': SAMPLE_RATE_IN_HZ, 
    'ibuf': WAV_SAMPLE_SIZE_IN_BYTES,
    'nch': NUM_CHANNELS}
# ── I2S and Audio CONFIGURATION ───────────────────────────────────────────────
# ── State machine ─────────────────────────────────────────────────────────────
RECORD = 0
PAUSE  = 1
RESUME = 2
STOP   = 3

STATE_MACHINE = {
    'RECORD': RECORD,
    'PAUSE': PAUSE,
    'RESUME': RESUME,
    'STOP': STOP
}
# ── State machine ─────────────────────────────────────────────────────────────
# ── Modules ───────────────────────────────────────────────────────────────────
LED_SLOT            = "D" # LED Tower - pin 4 - slot D
BUTTON_SLOT         = "E" # Button - pin 20 - slot G
BUZZER_SLOT         = "F" # Buzzer - pin 26 - slot F

OUTER_MODULES = {
    'LED': LED_SLOT,
    'BUTTON': BUTTON_SLOT,
    'BUZZER': BUZZER_SLOT
}
# ── Modules ───────────────────────────────────────────────────────────────────
## ─ Outer PiBody Configuration ────────────────────────────────────────────────

## ─ Inner PiBody Configuration ────────────────────────────────────────────────
# ── MODULES ───────────────────────────────────────────────────────────────────
CLIMATE_SLOT        = "D" # I2C  - pin 4  - slot D
LIGHT_SENSOR_SLOT   = "C" # ADC0 - pin 28 - slot C
SOIL_MOISTURE_SLOT  = "F" # ADC2 - pin 26 - slot F
MOTION_SENSOR_SLOT  = "G" # PIN  - pin 16 - slot G
SENSORS_PIN         = {
    'CLIMATE': CLIMATE_SLOT,
    'LIGHT': LIGHT_SENSOR_SLOT,
    'SOIL_MOISTURE': SOIL_MOISTURE_SLOT,
    'MOTION': MOTION_SENSOR_SLOT
}

LED_TOWER_SLOT      = "B" # LED Tower - pin 2 - slot B
WINDOW_1_SLOT       = 8   # Servo     - pin 8
WINDOW_2_SLOT       = 9   # Servo     - pin 9
DOOR_SLOT           = 19  # Servo     - pin 18 - slot H
FAN_LED_SLOT        = "A" # LED Tower - pin 0 - slot A
FAN_SLOT            = 6   # PIN      - pin 6 - slot E  
PUMP_SLOT           = 7   # PIN      - pin 7 - slot E
ACTUATORS_PIN         = {
    'WINDOW_1': WINDOW_1_SLOT,
    'WINDOW_2': WINDOW_2_SLOT,
    'DOOR': DOOR_SLOT,
    'LED_TOWER': LED_TOWER_SLOT,
    'FAN_LED': FAN_LED_SLOT,
    'FAN': FAN_SLOT,
    'PUMP': PUMP_SLOT
}
# ── MODULES ───────────────────────────────────────────────────────────────────
## ─ Inner PiBody Configuration ────────────────────────────────────────────────