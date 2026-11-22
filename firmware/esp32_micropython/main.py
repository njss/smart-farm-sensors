# Smart farm kit firmware for ESP32 (MicroPython)
#
# Publishes the SAME JSON as simulator.py to the SAME topics, so the chatbot
# and the digital twin work with real hardware without any change.
#
# Typical low-cost kit wiring (change the pins in config.py to match yours):
#   DHT22 air temperature/humidity  -> GPIO 4
#   Capacitive soil moisture v1.2   -> GPIO 34 (ADC)
#   LDR light module (analog out)   -> GPIO 35 (ADC)
#   Rain sensor module (analog out) -> GPIO 32 (ADC)
#   DS18B20 soil temperature        -> GPIO 15 (optional, 4.7k pull-up)
#   Relay for the water pump        -> GPIO 26
#
# Flash MicroPython, copy config.py and main.py to the board (e.g. with Thonny),
# and reset. Requires the built-in modules network, dht, machine and umqtt.simple
# (install umqtt with:  import mip; mip.install("umqtt.simple")).

import json
import time

import dht
import machine
import network
from umqtt.simple import MQTTClient

import config

ROOT = "ecocomp/smartfarm/" + config.FARM_ID
T_TELEMETRY = ROOT + "/telemetry"
T_STATUS = ROOT + "/status"
T_PUMP = ROOT + "/cmd/pump"

air = dht.DHT22(machine.Pin(config.PIN_DHT))
soil_adc = machine.ADC(machine.Pin(config.PIN_SOIL))
light_adc = machine.ADC(machine.Pin(config.PIN_LIGHT))
rain_adc = machine.ADC(machine.Pin(config.PIN_RAIN))
for adc in (soil_adc, light_adc, rain_adc):
    adc.atten(machine.ADC.ATTN_11DB)   # full 0-3.3 V range
pump = machine.Pin(config.PIN_PUMP, machine.Pin.OUT, value=0)

soil_temp_sensor = None
if config.PIN_DS18B20 is not None:
    import ds18x20
    import onewire
    ow = ds18x20.DS18X20(onewire.OneWire(machine.Pin(config.PIN_DS18B20)))
    roms = ow.scan()
    soil_temp_sensor = (ow, roms[0]) if roms else None


def scale(raw, dry, wet, low, high):
    """Linear calibration from raw ADC counts to a physical range."""
    if dry == wet:
        return low
    value = low + (raw - dry) * (high - low) / (wet - dry)
    return max(min(low, high), min(max(low, high), value))


def read_sensors():
    air.measure()
    reading = {
        "farm_id": config.FARM_ID,
        "ts": None,   # filled below if NTP time is available
        "soil_moisture": round(scale(soil_adc.read(), config.SOIL_DRY, config.SOIL_WET, 0, 50), 1),
        "air_temperature": round(air.temperature(), 1),
        "air_humidity": round(air.humidity(), 1),
        "light": int(scale(light_adc.read(), config.LIGHT_DARK, config.LIGHT_SUN, 0, 100000)),
        "rainfall": round(scale(rain_adc.read(), config.RAIN_DRY, config.RAIN_WET, 0, 20), 1),
        "pump": "on" if pump.value() else "off",
        "scenario": "real",
        "source": "esp32",
    }
    if soil_temp_sensor:
        ow, rom = soil_temp_sensor
        ow.convert_temp()
        time.sleep_ms(750)
        reading["soil_temperature"] = round(ow.read_temp(rom), 1)
    else:
        reading["soil_temperature"] = reading["air_temperature"]
    t = time.gmtime()
    if t[0] >= 2024:
        reading["ts"] = "%04d-%02d-%02dT%02d:%02d:%02dZ" % t[:6]
    return reading


def on_message(topic, msg):
    if topic.decode() == T_PUMP:
        try:
            state = json.loads(msg).get("state", "off")
        except ValueError:
            return
        pump.value(1 if state == "on" else 0)
        print("pump ->", state)


def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        for _ in range(40):
            if wlan.isconnected():
                break
            time.sleep(0.5)
    print("wifi:", wlan.ifconfig())
    try:
        import ntptime
        ntptime.settime()
    except Exception:
        pass
    client = MQTTClient("esp32-" + config.FARM_ID, config.BROKER, port=config.PORT, keepalive=60)
    client.set_last_will(T_STATUS, "offline", retain=True)
    client.set_callback(on_message)
    client.connect()
    client.publish(T_STATUS, "online", retain=True)
    client.subscribe(T_PUMP)
    return client


client = connect()
last = 0
while True:
    try:
        client.check_msg()
        if time.ticks_diff(time.ticks_ms(), last) > config.INTERVAL_S * 1000:
            last = time.ticks_ms()
            data = read_sensors()
            client.publish(T_TELEMETRY, json.dumps(data), retain=True)
            print(data)
        time.sleep_ms(100)
    except OSError as exc:
        print("connection lost, reconnecting:", exc)
        time.sleep(5)
        client = connect()
