"""Simple, transparent weather and soil model for a small smart-farm plot.

The model is intentionally easy to read: students should be able to open this
file, understand every line, and change it during the workshop. It is NOT an
agronomic research model. Real data from the farm kit replaces it later.

Units
-----
soil_moisture      % volumetric water content (VWC), 0-60
soil_temperature   degrees Celsius
air_temperature    degrees Celsius
air_humidity       % relative humidity
light              lux (full tropical sun is roughly 100 000 lux)
rainfall           mm per hour (rate during the last step)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

SCENARIOS = {
    # name:        (base temp, temp swing, rain chance per hour, rain mm/h range, cloudiness)
    "normal":     (17.0, 10.0, 0.04, (0.5, 4.0), 0.25),
    "drought":    (20.0, 12.0, 0.00, (0.0, 0.0), 0.05),
    "heatwave":   (24.0, 13.0, 0.00, (0.0, 0.0), 0.05),
    "heavy_rain": (16.0, 5.0, 0.60, (6.0, 25.0), 0.80),
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class FarmState:
    """Current state of the simulated plot."""

    hour: float = 6.0                 # simulated local time of day (0-24)
    soil_moisture: float = 32.0
    soil_temperature: float = 19.0
    air_temperature: float = 18.0
    air_humidity: float = 70.0
    light: float = 0.0
    rainfall: float = 0.0
    pump_on: bool = False
    scenario: str = "normal"
    rng: random.Random = field(default_factory=random.Random, repr=False)

    def step(self, dt_hours: float) -> None:
        """Advance the plot by ``dt_hours`` simulated hours."""
        base_t, swing, rain_p, rain_range, cloud = SCENARIOS[self.scenario]
        self.hour = (self.hour + dt_hours) % 24

        # Sun: 0 at night, 1 at solar noon (06:00 sunrise, 18:00 sunset near the equator).
        sun = max(0.0, math.sin(math.pi * (self.hour - 6.0) / 12.0))

        # Rain: a random shower starts with probability rain_p per simulated hour.
        raining = self.rng.random() < 1 - (1 - rain_p) ** dt_hours
        self.rainfall = round(self.rng.uniform(*rain_range), 1) if raining else 0.0
        cloud_now = 0.9 if raining else cloud * self.rng.uniform(0.5, 1.5)

        # Air temperature peaks ~2 h after noon; humidity moves the opposite way.
        lagged_sun = max(0.0, math.sin(math.pi * (self.hour - 8.0) / 12.0))
        target_t = base_t + swing * lagged_sun * (1 - 0.5 * cloud_now)
        self.air_temperature += (target_t - self.air_temperature) * min(1.0, dt_hours * 0.8)
        self.air_temperature += self.rng.gauss(0, 0.15)

        target_h = 95.0 if raining else clamp(88 - 45 * lagged_sun - (8 if self.scenario in ("drought", "heatwave") else 0), 15, 98)
        self.air_humidity += (target_h - self.air_humidity) * min(1.0, dt_hours * 0.8)
        self.air_humidity = clamp(self.air_humidity + self.rng.gauss(0, 0.5), 10, 100)

        self.light = max(0.0, 100_000 * sun * (1 - 0.8 * clamp(cloud_now, 0, 1)) + self.rng.gauss(0, 300) * sun)

        # Soil temperature follows air temperature slowly.
        self.soil_temperature += (self.air_temperature - 2.0 - self.soil_temperature) * min(1.0, dt_hours * 0.15)

        # Water balance (in % VWC per hour, deliberately simplified):
        #   evapotranspiration grows with sun, heat and dry air;
        #   rain and the irrigation pump add water; drainage removes excess above field capacity.
        # 1.1 is exaggerated (about 3x real field rates) so changes are visible during a workshop.
        et = 1.1 * sun * (self.air_temperature / 25.0) * (1 - self.air_humidity / 110.0)
        gain = 0.35 * self.rainfall + (5.0 if self.pump_on else 0.0)
        drainage = 0.25 * max(0.0, self.soil_moisture - 40.0)
        self.soil_moisture = clamp(self.soil_moisture + (gain - et - drainage) * dt_hours, 5.0, 58.0)

    def reading(self) -> dict:
        """Values rounded the way a real sensor would report them."""
        return {
            "soil_moisture": round(self.soil_moisture, 1),
            "soil_temperature": round(self.soil_temperature, 1),
            "air_temperature": round(self.air_temperature, 1),
            "air_humidity": round(self.air_humidity, 1),
            "light": int(self.light),
            "rainfall": self.rainfall,
            "pump": "on" if self.pump_on else "off",
            "scenario": self.scenario,
            "sim_time": f"{int(self.hour):02d}:{int((self.hour % 1) * 60):02d}",
        }
