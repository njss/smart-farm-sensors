#!/usr/bin/env python3
"""Record every telemetry message for a farm into a CSV file.

The CSV is the dataset students explore and use to train simple models
(for example: predict tomorrow's soil moisture, or classify "needs irrigation").

    python logger.py --farm iringa-demo --out data/iringa-demo.csv
    python logger.py --farm "+" --out data/all-farms.csv        # every farm on the broker
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

from smartfarm import topics

FIELDS = ["ts", "farm_id", "sim_time", "soil_moisture", "soil_temperature", "air_temperature",
          "air_humidity", "light", "rainfall", "pump", "scenario", "source"]


def main(argv=None) -> int:
    import paho.mqtt.client as mqtt

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--broker", default=topics.DEFAULT_BROKER)
    p.add_argument("--port", type=int, default=topics.DEFAULT_TCP_PORT)
    p.add_argument("--farm", default=topics.DEFAULT_FARM_ID, help="farm id, or + for all farms")
    p.add_argument("--out", default="data/readings.csv")
    args = p.parse_args(argv)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    new_file = not os.path.exists(args.out)
    fh = open(args.out, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
    if new_file:
        writer.writeheader()

    def on_connect(c, userdata, flags, reason_code, properties):
        c.subscribe(topics.telemetry(args.farm))
        print(f"[logger] subscribed to {topics.telemetry(args.farm)} -> {args.out}")

    def on_message(c, userdata, msg):
        try:
            row = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        writer.writerow(row)
        fh.flush()
        print(f"{row.get('ts')} {row.get('farm_id')} soil={row.get('soil_moisture')}% "
              f"air={row.get('air_temperature')}C rain={row.get('rainfall')}mm/h pump={row.get('pump')}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, keepalive=30)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    finally:
        fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
