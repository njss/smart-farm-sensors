# 📡 Smart Farm Sensors

Part of the **Smart Farm workshop kit** for the Africa-UniNet project *Developing AI Competency for Sustainability in Ethiopia and Tanzania* (smart agriculture).

This repo produces the farm data that every other app uses:

- **`simulator.py`**: a simulated farm plot (soil moisture, soil and air temperature, humidity, light, rainfall, irrigation pump) that publishes over MQTT. No hardware needed.
- **`logger.py`**: records the data stream to CSV, so you can analyse it and train models in Python.
- **`firmware/esp32_micropython/`**: code for a real ESP32 smart-farm kit that publishes **the same messages**, so the chatbot and the digital twin work unchanged with real sensors.

The shared message format is in [TOPICS.md](TOPICS.md).

| Sibling repo | What it does |
|---|---|
| `smart-farm-chatbot` | Farmer advisory chatbot (English / Swahili) that reads this data |
| `smart-farm-twin` | 3D digital twin of the plot, with VR |
| `smart-farm-pbl-studio` | The PBL / design-thinking workshop path |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python simulator.py --farm team-1
```

Then open the digital twin or the chatbot and type `team-1` as the farm id.

Useful options:

```bash
python simulator.py --scenario drought            # normal | drought | heatwave | heavy_rain
python simulator.py --speed 600                   # 1 real second = 10 farm minutes
python simulator.py --auto-irrigate 22            # pump on below 22 % soil moisture
python simulator.py --dry-run --count 5           # no network, just print readings
python simulator.py --broker localhost            # your own broker (e.g. Mosquitto)
```

The simulator also listens for commands: the **Toggle pump** buttons in the twin and the chatbot switch its pump, and the twin's scenario buttons change the weather.

## Record a dataset

```bash
python logger.py --farm team-1 --out data/team-1.csv
```

```python
import pandas as pd
df = pd.read_csv("data/team-1.csv", parse_dates=["ts"])
df.plot(x="ts", y=["soil_moisture", "air_temperature"])
```

## Real hardware (ESP32 + MicroPython)

1. Flash MicroPython on the ESP32 and install `umqtt.simple` (`import mip; mip.install("umqtt.simple")`).
2. Edit `firmware/esp32_micropython/config.py`: Wi-Fi, farm id, pins, and calibration values.
3. Copy `config.py` and `main.py` to the board (Thonny works well) and reset.

Default wiring: DHT22 on GPIO 4, capacitive soil moisture on GPIO 34, LDR on GPIO 35, rain sensor on GPIO 32, pump relay on GPIO 26, optional DS18B20 soil probe. **Calibrate the soil probe** (dry air vs. glass of water) before trusting the numbers.

## How the simulator works

Open [`smartfarm/model.py`](smartfarm/model.py): every rule is a few lines of plain Python. The sun follows the time of day, temperature and humidity follow the sun, and soil moisture follows a simple water balance:

```
change in soil moisture = rain + irrigation − evapotranspiration − drainage
```

Evapotranspiration is deliberately **about 3× faster than in a real field**, so changes are visible within a workshop session.

## 🧑🏾‍🎓 Student tasks

1. **Explore.** Run the simulator in each scenario for 5 minutes. Which sensor reacts first to a heatwave? Which reacts to rain?
2. **Analyse.** Log 30 minutes of data. Plot soil moisture against time and mark when the pump was on.
3. **Improve the model.** Add a new sensor (for example wind speed or soil pH) to `model.py` and the payload. Update TOPICS.md and tell the chatbot team.
4. **Predict.** Train a simple model (linear regression or a decision tree in scikit-learn) that predicts soil moisture one hour ahead. When would that help a farmer?
5. **Go physical.** Wire a real sensor to the ESP32 and publish to your team's farm id. Compare real and simulated data.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## License

MIT. See [LICENSE](LICENSE).
