"""Constants for ElectroS EV Charger integration."""

DOMAIN = "electros_ev"
DEFAULT_SCAN_INTERVAL = 60

CONF_CHARGER_LOGIN = "charger_login"
CONF_CHARGER_PASSWORD = "charger_password"
CONF_HOST = "host"  # optional: charger IP/hostname for local (no-cloud) connection
DEFAULT_LOCAL_PORT = 80
DEFAULT_LOCAL_WS_PATH = "/ws"
CONF_WS_HOST = "ws_host"
CONF_WS_PATH = "ws_path"
CONF_WS_ORIGIN = "ws_origin"
CONF_WS_PROTOCOL = "ws_protocol"
CONF_BASE_URL = "base_url"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_WS_HOST = "electros.org.ua"
DEFAULT_WS_PATH = "/ws/"
DEFAULT_WS_ORIGIN = "https://electros.org.ua"
DEFAULT_WS_PROTOCOL = "example-protocol"
DEFAULT_BASE_URL = "https://electros.org.ua/auth/"

AMP_TO_INDEX = {
    32: 0,
    30: 1,
    28: 2,
    26: 3,
    24: 4,
    22: 5,
    20: 6,
    18: 7,
    16: 8,
    14: 9,
    12: 10,
    10: 11,
    8: 12,
    6: 13,
}

SUPPORTED_AMPS = sorted(AMP_TO_INDEX)

STATUS_TEXT = {
    "0": "Очікування авто",
    "1": "Авто підключено",
    "2": "Заряджає",
    "3": "Помилка зарядки",
    "4": "Зарядку заблоковано",
    "5": "Низька напруга мережі",
    "6": "Помилка зв'язку",
    "7": "Офлайн",
    "16": "Витік струму",
}

STATUS_TEXT_EN = {
    "0": "waiting_for_vehicle",
    "1": "vehicle_connected_idle",
    "2": "charging",
    "3": "charging_fault",
    "4": "charging_blocked",
    "5": "mains_voltage_low",
    "6": "charger_communication_fault",
    "7": "offline",
    "16": "leakage_current_fault",
}
