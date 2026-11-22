#!/usr/bin/env python3
"""Smart farm sensor simulator.

Publishes realistic sensor readings for one farm plot over MQTT, using the
shared topics in TOPICS.md, and reacts to pump and scenario commands.

Examples
--------
    python simulator.py                                  # demo farm, public broker
    python simulator.py --farm team-3 --speed 120        # 1 real second = 2 simulated minutes
    python simulator.py --scenario drought
    python simulator.py --broker localhost --port 1883   # your own broker
    python simulator.py --dry-run                        # print readings, no network
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone

from smartfarm import topics
from smartfarm.model import SCENARIOS, FarmState


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--broker", default=topics.DEFAULT_BROKER, help="MQTT broker host (default: %(default)s)")
    p.add_argument("--port", type=int, default=topics.DEFAULT_TCP_PORT, help="MQTT port (default: %(default)s)")
    p.add_argument("--transport", choices=["tcp", "websockets"], default="tcp")
    p.add_argument("--tls", action="store_true", help="use TLS (e.g. HiveMQ Cloud on port 8883)")
    p.add_argument("--username", default=None)
    p.add_argument("--password", default=None)
    p.add_argument("--farm", default=topics.DEFAULT_FARM_ID, help="farm id used in the topic (default: %(default)s)")
    p.add_argument("--interval", type=float, default=2.0, help="real seconds between readings (default: %(default)s)")
    p.add_argument("--speed", type=float, default=300.0, help="simulated seconds per real second (default: %(default)s)")
    p.add_argument("--scenario", choices=sorted(SCENARIOS), default="normal")
    p.add_argument("--start-hour", type=float, default=7.0, help="simulated time of day to start (default: %(default)s)")
    p.add_argument("--seed", type=int, default=None, help="random seed for repeatable runs")
    p.add_argument("--auto-irrigate", type=float, default=None, metavar="PCT",
                   help="switch the pump on below PCT %% soil moisture and off 10 points higher")
    p.add_argument("--dry-run", action="store_true", help="print readings only, do not connect")
    p.add_argument("--count", type=int, default=0, help="stop after N readings (0 = run forever)")
    return p.parse_args(argv)


def build_payload(state: FarmState, farm_id: str) -> dict:
    return {
        "farm_id": farm_id,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        **state.reading(),
        "source": "simulator",
    }


def make_client(args, state: FarmState):
    import paho.mqtt.client as mqtt  # imported here so --dry-run works without paho installed

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"sim-{args.farm}-{random.randint(0, 99999)}",
        transport=args.transport,
    )
    if args.username:
        client.username_pw_set(args.username, args.password)
    if args.tls:
        client.tls_set()
    client.will_set(topics.status(args.farm), "offline", qos=1, retain=True)

    def on_connect(c, userdata, flags, reason_code, properties):
        print(f"[mqtt] connected to {args.broker}:{args.port} ({reason_code})")
        c.publish(topics.status(args.farm), "online", qos=1, retain=True)
        c.subscribe([(topics.cmd_pump(args.farm), 1), (topics.cmd_scenario(args.farm), 1)])

    def on_message(c, userdata, msg):
        try:
            data = json.loads(msg.payload.decode() or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            print(f"[cmd] ignored non-JSON message on {msg.topic}")
            return
        if msg.topic == topics.cmd_pump(args.farm):
            state.pump_on = str(data.get("state", "")).lower() == "on"
            print(f"[cmd] pump -> {'on' if state.pump_on else 'off'}")
        elif msg.topic == topics.cmd_scenario(args.farm) and data.get("scenario") in SCENARIOS:
            state.scenario = data["scenario"]
            print(f"[cmd] scenario -> {state.scenario}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, keepalive=30)
    client.loop_start()
    return client


def main(argv=None) -> int:
    args = parse_args(argv)
    state = FarmState(hour=args.start_hour, scenario=args.scenario, rng=random.Random(args.seed))
    client = None if args.dry_run else make_client(args, state)
    topic = topics.telemetry(args.farm)
    print(f"[sim] farm '{args.farm}' -> {topic} (scenario={args.scenario}, speed x{args.speed:g})")

    sent = 0
    try:
        while True:
            state.step(args.interval * args.speed / 3600.0)
            if args.auto_irrigate is not None:
                if state.soil_moisture < args.auto_irrigate:
                    state.pump_on = True
                elif state.soil_moisture > args.auto_irrigate + 10:
                    state.pump_on = False
            payload = build_payload(state, args.farm)
            line = json.dumps(payload)
            if client is not None:
                client.publish(topic, line, qos=0, retain=True)
            print(line, flush=True)
            sent += 1
            if args.count and sent >= args.count:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if client is not None:
            client.publish(topics.status(args.farm), "offline", qos=1, retain=True).wait_for_publish(3)
            client.loop_stop()
            client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
