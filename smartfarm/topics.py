"""Shared MQTT contract used by every workshop app.

Keep this file identical to TOPICS.md. If you change a topic or field here,
change it in the chatbot and the digital twin too.
"""

DEFAULT_BROKER = "broker.hivemq.com"   # free public broker: fine for a workshop, never for private data
DEFAULT_TCP_PORT = 1883
DEFAULT_WS_URL = "wss://broker.hivemq.com:8884/mqtt"   # what browsers use
DEFAULT_FARM_ID = "iringa-demo"
ROOT = "ecocomp/smartfarm"


def base(farm_id: str) -> str:
    return f"{ROOT}/{farm_id}"


def telemetry(farm_id: str) -> str:
    """JSON sensor reading, published retained every interval."""
    return f"{base(farm_id)}/telemetry"


def status(farm_id: str) -> str:
    """'online' or 'offline' (retained, offline is the Last Will)."""
    return f"{base(farm_id)}/status"


def cmd_pump(farm_id: str) -> str:
    """Command: {"state": "on"} or {"state": "off"}."""
    return f"{base(farm_id)}/cmd/pump"


def cmd_scenario(farm_id: str) -> str:
    """Command: {"scenario": "normal" | "drought" | "heatwave" | "heavy_rain"} (simulator only)."""
    return f"{base(farm_id)}/cmd/scenario"
