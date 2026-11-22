import json
import random

from simulator import build_payload, main
from smartfarm import topics
from smartfarm.model import FarmState


def run(scenario, hours=48, pump=False, seed=1):
    s = FarmState(scenario=scenario, rng=random.Random(seed), pump_on=pump)
    for _ in range(hours * 6):
        s.step(1 / 6)
    return s


def test_values_stay_in_physical_ranges():
    for scenario in ("normal", "drought", "heatwave", "heavy_rain"):
        s = FarmState(scenario=scenario, rng=random.Random(3))
        for _ in range(24 * 12):
            s.step(1 / 12)
            r = s.reading()
            assert 5 <= r["soil_moisture"] <= 58
            assert 0 <= r["air_humidity"] <= 100
            assert 0 <= r["light"] <= 100_000
            assert -5 < r["air_temperature"] < 45


def test_drought_dries_soil_and_rain_wets_it():
    assert run("drought").soil_moisture < 25
    assert run("heavy_rain").soil_moisture > 38


def test_pump_raises_moisture():
    assert run("drought", pump=True).soil_moisture > run("drought").soil_moisture + 10


def test_payload_matches_contract():
    p = build_payload(FarmState(rng=random.Random(0)), "team-1")
    for key in ("farm_id", "ts", "soil_moisture", "soil_temperature", "air_temperature",
                "air_humidity", "light", "rainfall", "pump", "scenario", "source"):
        assert key in p
    assert p["ts"].endswith("Z")
    json.dumps(p)


def test_topics():
    assert topics.telemetry("x") == "ecocomp/smartfarm/x/telemetry"
    assert topics.cmd_pump("x") == "ecocomp/smartfarm/x/cmd/pump"


def test_dry_run(capsys):
    assert main(["--dry-run", "--count", "3", "--interval", "0", "--seed", "1"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len([l for l in lines if l.startswith("{")]) == 3
