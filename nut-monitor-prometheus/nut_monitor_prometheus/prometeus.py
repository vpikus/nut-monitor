import enum
import logging.config
import os
import signal
import sys
import time
from typing import Dict, List, Union

import yaml
from nut_monitor_client import NutClient, NutSession
from nut_monitor_client.exceptions import NutClientConnectError
from prometheus_client import Enum, Gauge, Info, start_http_server

HOME_DIR = os.environ.get('NUT_PROMETEUS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = f"{HOME_DIR}/config"
LOG_DIR = os.environ.get('NUT_PROMETEUS_LOG_DIR', f"{HOME_DIR}/logs")
NUT_PROMETEUS_PORT = int(os.environ.get('NUT_PROMETEUS_PORT', 8000))

def setup_logging():
    with open(f"{CONFIG_DIR}/logging.yml", 'r') as file:
        config = yaml.safe_load(file.read())
    config['handlers']['file']['filename'] = f"{LOG_DIR}/nut-propmeteus-exporter.log"
    logging.config.dictConfig(config)

setup_logging()

def load_config_and_initialize():
    logging.info("Loading configuration")
    with open(f"{CONFIG_DIR}/application.yml", 'r') as file:
        config = yaml.safe_load(file)

    nut = {}
    for server_config in config['monitors']:
        logging.info(f"Configuring NUT client for {server_config["key"]} monitor")
        # Filter out the keys we want to pass to the NutClient
        filtered_config = {key: server_config[key] for key in ['host', 'port'] if key in server_config}
        nut[server_config["key"]] = NutClient(**filtered_config)
    return nut

METRIC_NAME_PREFIX = "upsmon"
UPS_STATUS_KEY = "ups.status"

CALC_UPS_STATUS_KEY = "calc.status.ups" # extracted from ups.status
CALC_ALARM_STATUS_KEY = "calc.status.alarm" # extracted from ups.status
CALC_BATTERY_STATUS_KEY = "calc.status.battery" # extracted from ups.status
CALC_REALPOWER_KEY = "calc.ups.realpower" # calculated from ups.load and ups.realpower.nominal

nut: dict[str, NutClient] = load_config_and_initialize()

service_metrics: Dict[str, Union[Gauge, Enum, Info]] = {}

gauge_metric_config = {
    "device.uptime": {
        "description": "Device uptime in seconds",
        "value-type": int
    },
    "ups.load": {
        "description": "UPS load (percent)",
        "value-type": int
    },
    "ups.temperature": {
        "description": "UPS temperature (degrees C)",
        "value-type": float
    },
    "battery.charge": {
        "description": "Battery charge (percent)",
        "value-type": int
    },
    "battery.charge.low": {
        "description": "Remaining battery level when UPS switches to LB (percent)",
        "value-type": int
    },
    "battery.charge.warning": {
        "description": 'Battery level when UPS switches to "Warning" state (percent)',
        "value-type": int
    },
    "battery.charge.restart": {
        "description": "Minimum battery level for UPS restart after power-off",
        "value-type": int
    },
    "battery.runtime": {
        "description": "Remaining battery runtime (seconds)",
        "value-type": int
    },
    "battery.runtime.low": {
        "description": "Remaining battery runtime when UPS switches to LB (seconds)",
        "value-type": int
    },
    "battery.runtime.restart": {
        "description": "Minimum battery runtime for UPS restart after power-off (seconds)",
        "value-type": int
    },
    "ups.delay.shutdown": {
        "description": "Interval to wait before shutting down the load (seconds)",
        "value-type": int
    },
    "ups.delay.start": {
        "description": "Interval to wait before restarting the load (seconds)",
        "value-type": int
    },
    "battery.voltage": {
        "description": "Battery voltage (V)",
        "value-type": float
    },
    "battery.voltage.nominal": {
        "description": "Nominal battery voltage (V)",
        "value-type": float
    },
    "battery.voltage.high": {
        "description": "Maximum battery voltage (V)",
        "value-type": float
    },
    "battery.voltage.low": {
        "description": "Minimum battery voltage (V)",
        "value-type": float
    },
    "battery.temperature": {
        "description": "Battery temperature (degrees C)",
        "value-type": float
    },
    "input.voltage": {
        "description": "Input voltage (V)",
        "value-type": float
    },
    "input.voltage.nominal": {
        "description": "Nominal input voltage (V)",
        "value-type": float
    },
    "input.voltage.minimum": {
        "description": "Minimum incoming voltage seen (V)",
        "value-type": float
    },
    "input.voltage.maximum": {
        "description": "Maximum incoming voltage seen (V)",
        "value-type": float
    },
     "input.transfer.high": {
        "description": "High voltage transfer point (V)",
        "value-type": int
    },
    "input.transfer.low": {
        "description": "Low voltage transfer point (V)",
        "value-type": int
    },
    "input.current": {
        "description": "Input current (A)",
        "value-type": float
    },
    "input.current.nominal": {
        "description": "Nominal input current (A)",
        "value-type": float
    },
    "input.frequency": {
        "description": "Input line frequency (Hz)",
        "value-type": float
    },
    "input.frequency.nominal": {
        "description": "Nominal input line frequency (Hz)",
        "value-type": float
    },
    "input.frequency.low": {
        "description": "Input line frequency low (Hz)",
        "value-type": float
    },
    "input.frequency.high": {
        "description": "Input line frequency high (Hz)",
        "value-type": float
    },
    "output.voltage": {
        "description": "Output voltage (V)",
        "value-type": float
    },
    "output.voltage.nominal": {
        "description": "Nominal output voltage (V)",
        "value-type": float
    },
    "output.current": {
        "description": "Output current (A)",
        "value-type": float
    },
    "output.current.nominal": {
        "description": "Nominal output current (A)",
        "value-type": float
    },
    "output.frequency": {
        "description": "Output frequency (Hz)",
        "value-type": float
    },
    "output.frequency.nominal": {
        "description": "Nominal output frequency (Hz)",
        "value-type": float
    },
    "ups.power": {
        "description": "Current value of apparent power (Volt-Amps)",
        "value-type": float
    },
    "ups.power.nominal": {
        "description": "Nominal value of apparent power (Volt-Amps)",
        "value-type": int
    },
    "ups.realpower": {
        "description": "Current value of real power (Watts)",
        "value-type": int
    },
    CALC_REALPOWER_KEY: {
        "description": "[Calculated] Current value of real power (Watts)",
        "value-type": float
    },
    "ups.realpower.nominal": {
        "description": "Nominal value of real power (Watts)",
        "value-type": int
    }
}

# TODO Add:
# - input.frequency.status
# - input.current.status

enum_metric_config = {
    "ups.beeper.status": {
        "description": "UPS beeper status (enabled, disabled or muted)",
        "states": [
            "disabled",
            "enabled",
            "muted" # Temporarily muted
        ]
    },
    CALC_UPS_STATUS_KEY: {
        "description": "UPS status (extracted from ups.status)",
        "states": [
            "OFF", # UPS is offline and is not supplying power to the load
            "OL", # On line (mains is present)
            "OB" # On battery (mains is not present)
        ]
    },
    "battery.charger.status": {
        "description": "Battery charger status",
        "states": [
            "resting", # the battery is fully charged, and not charging nor discharging
            "charging", # battery is charging
            "discharging", # battery is discharging
            "floating" # battery has completed its charge cycle, and waiting to go to resting mode
        ]
    },
    CALC_BATTERY_STATUS_KEY: {
        "description": "Battery status (extracted from ups.status)",
        "states": [
            "NONE", # the battery is fully charged, and not charging nor discharging
            "CHRG", # battery is charging
            "DISCHRG" # battery is discharging
        ]
    },
    CALC_ALARM_STATUS_KEY: {
        "description": "UPS alarm status (extracted from ups.status)",
        "states": [
            "LB", # Low battery
            "HB", # High battery
            "RB", # Battery needs to be replaced
            "BYPASS", # UPS bypass circuit is active -- no battery protection is available
            "CAL", # UPS is currently performing a runtime calibration (on battery)
            "OVER", # UPS is overloaded
            "TRIM", # UPS is trimming incoming voltage (called "buck" in some hardware)
            "BOOST", # UPS is boosting incoming voltage
            "FSD" # UPS is on forced shutdown
        ]
    }
}

info_metric_config = {
    "input.transfer.reason": {
        "description": "Reason for last transfer to battery",
    },
    "ups.test.result": {
        "description": "Result of last self-test",
    },
    "ups.alarm": {
        "description": "UPS alarm status"
    },
    "ups.status": {
        "description": "UPS status"
    }
}

def init_metrics():
    for varname, config in gauge_metric_config.items():
        metric_key = varname.replace(".", "_")
        logging.debug(f"Initializing metric {METRIC_NAME_PREFIX}_{metric_key}")
        service_metrics[varname] = Gauge(f"{METRIC_NAME_PREFIX}_{metric_key}", config["description"], ["ups"])

    for varname, config in enum_metric_config.items():
        metric_key = varname.replace(".", "_")
        logging.debug(f"Initializing metric {METRIC_NAME_PREFIX}_{metric_key}")
        service_metrics[varname] = Enum(f"{METRIC_NAME_PREFIX}_{metric_key}", config["description"], ["ups"], states=config["states"])

    for varname, config in info_metric_config.items():
        metric_key = varname.replace(".", "_")
        logging.debug(f"Initializing metric {METRIC_NAME_PREFIX}_{metric_key}")
        service_metrics[varname] = Info(f"{METRIC_NAME_PREFIX}_{metric_key}", config["description"], ["ups"])

def unwrap_legacy_ups_status(statistics: Dict[str, str]):
    original_status = statistics[UPS_STATUS_KEY]
    parts = original_status.split(" ")

    if parts[0] == "ALARM":
        alarm_type = parts[-1]  # Assuming the last part is the alarm type
        statistics[CALC_ALARM_STATUS_KEY] = alarm_type
        parts = parts[1:-1]  # Remove the ALARM part and the alarm type

    if parts:
        statistics[CALC_UPS_STATUS_KEY] = parts[0]
    else:
        logging.error("Missing UPS status after processing ALARM. Check UPS status configuration.")
        return

    if len(parts) > 1:
        battery_status = parts[1]
        statistics[CALC_BATTERY_STATUS_KEY] = battery_status
    else:
        # If the battery status is not present, assume it's resting
        statistics[CALC_BATTERY_STATUS_KEY] = "NONE"

def calculate_ups_power(statistics: Dict[str, str]):
    try:
        load_pct = int(statistics.get("ups.load"))
        real_power_nominal = int(statistics.get("ups.realpower.nominal"))
        power = real_power_nominal * load_pct / 100
    except ValueError:
        power = 0

    statistics[CALC_REALPOWER_KEY] = str(power)

def safe_remove_metric(key, ups):
    if key in service_metrics:
        try:
            service_metrics[key].remove(ups)
        except Exception:
            pass

def fetch_data(session: NutSession, ups: str):
    upsname, _ = ups.split("@")
    statistics = session.list_vars(upsname)
    calculate_ups_power(statistics)
    unwrap_legacy_ups_status(statistics)

    for varname, config in gauge_metric_config.items():
        value = statistics.get(varname)
        if value:
            try:
                value = config["value-type"](value)
                service_metrics[varname].labels(ups=ups).set(value)
            except Exception:
                logging.exception(f"Failed to set value for {varname} with value '{value}'")
        else:
            safe_remove_metric(varname, ups)

    for varname, config in enum_metric_config.items():
        value = statistics.get(varname)
        if value:
            try:
                service_metrics[varname].labels(ups=ups).state(value)
            except Exception:
                logging.exception(f"Failed to set value for {varname} with value '{value}'")
        else:
            safe_remove_metric(varname, ups)

    for varname, config in info_metric_config.items():
        value = statistics.get(varname)
        if value:
            try:
                service_metrics[varname].labels(ups=ups).info({varname.replace('.', '_'): value})
            except Exception:
                logging.exception(f"Failed to set value for {varname} with value '{value}'")
        else:
            safe_remove_metric(varname, ups)

def fetch_all_data():
    """Fetch all data for all UPSes."""

    with nut["rpi5"].session() as session:
        for upsname in session.list_ups():
            ups = f"{upsname}@{nut["rpi5"].host}"
            try:
                fetch_data(session, ups)
            except Exception:
                logging.exception(f"Failed to fetch data for {ups}")
                for key in service_metrics:
                    safe_remove_metric(key, ups)

UPS_INFO_VARS = [
    "device.description",
    "device.model",
    "device.mfr",
    "device.serial",
    "device.type",
    "device.contact",
    "device.location",
    "device.part",
    "device.macaddr"
]

UPS_DRIVER_INFO_VARS = [
    "driver.name",
    "driver.version",
    "driver.version.internal",
    "driver.version.data",
    "driver.version.usb",
    "driver.flag.*",
    "driver.parameter.*"
]

def get_veriables(varnames: List[str], vars_dict: Dict[str, str]) -> Dict[str, str]:
    transformed_dict = {}
    for varname in varnames:
        if "*" in varname:  # Handle wildcard keys
            prefix = varname.replace('*', '')
            for original_key in vars_dict:
                if original_key.startswith(prefix):
                    transformed_key = original_key.replace('.', '_')
                    transformed_dict[transformed_key] = vars_dict[original_key]
        else:  # Handle normal keys
            if varname in vars_dict:
                transformed_key = varname.replace('.', '_')
                transformed_dict[transformed_key] = vars_dict[varname]
    return transformed_dict

# Should be called after initializing the metrics. And must not be cleared.
service_info_metrics: Dict[str, Info] = {}

def initialize_ups():
    ups_info = Info(f"{METRIC_NAME_PREFIX}_ups", "UPS metadata", ["ups"])
    service_info_metrics["ups.info"] = ups_info
    ups_driver_info = Info(f"{METRIC_NAME_PREFIX}_ups_driver", "UPS driver metadata", ["ups"])
    service_info_metrics["ups.driver.info"] = ups_driver_info

    with nut["rpi5"].session() as session:
        for upsname in session.list_ups():
            ups = f"{upsname}@{nut["rpi5"].host}"
            ups_vars = session.list_vars(upsname)
            ups_info.labels(ups = ups).info(get_veriables(UPS_INFO_VARS, ups_vars))
            ups_driver_info.labels(ups = ups).info(get_veriables(UPS_DRIVER_INFO_VARS, ups_vars))
            init_metrics()

def clear_metrics():
    for key in service_metrics:
        try:
            service_metrics[key].clear()
        except Exception:
            logging.exception(f"Failed to clear metric {key}")

class State(enum.Enum):

    def __init__(self, delay):
        self.delay = delay

    OK = 5
    CONNECTION_ERROR = 60
    FATAL_ERROR = 30

def shutdown(signum, frame):
    logging.getLogger().info("Shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logging.getLogger().setLevel(logging.INFO)
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.INFO)

    start_http_server(NUT_PROMETEUS_PORT)

    initialize_ups()

    state: State = State.OK
    while True:
        try:
            fetch_all_data()
            if state == State.CONNECTION_ERROR:
                logging.info("Connection reestablished")
            state = State.OK
        except NutClientConnectError as e:
            if state != State.CONNECTION_ERROR:
                logging.error(f"Failed to establish session: {e}")
                state = State.CONNECTION_ERROR
        except Exception:
            state = State.FATAL_ERROR
            logging.exception("An unexpected error occurred")

        if state != State.OK:
            clear_metrics()
        time.sleep(state.delay)
