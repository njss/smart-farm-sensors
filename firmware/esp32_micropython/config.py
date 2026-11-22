# Edit these values for your board and network. Do not commit real Wi-Fi passwords.

WIFI_SSID = "your-wifi"
WIFI_PASSWORD = "your-password"

BROKER = "broker.hivemq.com"
PORT = 1883
FARM_ID = "iringa-demo"      # each team uses its own id, e.g. "team-3"
INTERVAL_S = 10              # seconds between readings

PIN_DHT = 4
PIN_SOIL = 34
PIN_LIGHT = 35
PIN_RAIN = 32
PIN_PUMP = 26
PIN_DS18B20 = None           # e.g. 15 if you have a waterproof soil temperature probe

# Calibration (raw ADC counts, 0-4095). Measure your own:
#   soil probe in dry air -> SOIL_DRY ; in a glass of water -> SOIL_WET
SOIL_DRY = 3300
SOIL_WET = 1300
LIGHT_DARK = 4000
LIGHT_SUN = 200
RAIN_DRY = 4095
RAIN_WET = 1200
