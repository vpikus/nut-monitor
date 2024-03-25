import logging.config
import os
import signal
import sys
import time
from typing import Dict, List, Union

import yaml
from nutclient import NutClient, NutSession
from prometheus_client import Enum, Gauge, Info, start_http_server

HOME_DIR = os.environ.get('NUT_PROMETEUS_HOME', os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = f"{HOME_DIR}/config"
LOG_DIR = os.environ.get('NUT_PROMETEUS_LOG_DIR', f"{HOME_DIR}/logs")

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
    "ups.realpower.nominal": {
        "description": "Nominal value of real power (Watts)",
        "value-type": int
    }
}

# TODO Add:
# - input.frequency.status
# - input.current.status

UPS_STATUS_STATES = [
    "OL",
    "OB",
    "LB",
    "HB",
    "RB",
    "CHRG",
    "DISCHRG",
    "BYPASS",
    "CAL",
    "OFF",
    "OVER",
    "TRIM",
    "BOOST",
    "FSD"
]

UPS_BEEPER_STATUS_STATES = [
    "enabled",
    "disabled",
    "muted"
]

enum_metric_config = {
    "ups.beeper.status": {
        "description": "UPS beeper status (enabled, disabled or muted)",
        "states": UPS_BEEPER_STATUS_STATES.copy()
    },
    "ups.status": {
        "description": "UPS status",
        "states": UPS_STATUS_STATES.copy()
    },
    "battery.charger.status": {
        "description": "Battery charger status",
        "states": ["charging", "discharging", "floating", "resting"] + UPS_STATUS_STATES.copy()
    }
}

def init_metrics():
    for varname in gauge_metric_config:
        metric_key = varname.replace(".", "_")
        logging.debug(f"Initializing metric {METRIC_NAME_PREFIX}_{metric_key}")
        service_metrics[varname] = Gauge(f"{METRIC_NAME_PREFIX}_{metric_key}", gauge_metric_config[varname]["description"], ["ups"])

    for varname in enum_metric_config:
        metric_key = varname.replace(".", "_")
        logging.debug(f"Initializing metric {METRIC_NAME_PREFIX}_{metric_key}")
        metric_conf = enum_metric_config[varname]
        service_metrics[varname] = Enum(f"{METRIC_NAME_PREFIX}_{metric_key}", metric_conf["description"], ["ups"], states=metric_conf["states"])

def fetch_data(session: NutSession, ups: str):
    upsname, _ = ups.split("@")
    statistics = session.list_vars(upsname)
    for varname in gauge_metric_config:
        config = gauge_metric_config[varname]
        value = statistics.get(varname)
        if value is not None:
            gauge = service_metrics[varname]
            try:
                value = config["value-type"](value)
                gauge.labels(ups=ups).set(value)
                if varname == "ups.load" and "ups.power" not in statistics:
                    real_power_nominal = int(statistics.get("ups.realpower.nominal"))
                    service_metrics["ups.power"].labels(ups=ups).set(real_power_nominal / 100 * value)
            except Exception:
                logging.exception(f"Failed to set value for {varname} with value '{value}'")

    for varname in enum_metric_config:
        value = statistics.get(varname)
        if value is not None:
            try:
                enum = service_metrics[varname]
                if varname == "ups.status":
                    ups_status = value
                    battery_status = None
                    if value.find(" ") != -1:
                        ups_status, battery_status = value.split(" ")
                    enum.labels(ups=ups).state(ups_status)
                    if battery_status is not None:
                        service_metrics["battery.charger.status"].labels(ups=ups).state(battery_status)
                else:
                    enum.labels(ups=ups).state(value)
            except Exception as e:
                logging.exception(f"Failed to set value for {varname} with value '{value}'")

def shutdown(signum, frame):
    logging.getLogger().info("Shutting down...")
    sys.exit(0)

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

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logging.getLogger().setLevel(logging.INFO)
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.INFO)

    start_http_server(int(os.environ.get('NUT_PROMETEUS_PORT', 8000)))

    ups_info = Info(f"{METRIC_NAME_PREFIX}_ups", "UPS metadata", ["ups"])
    service_metrics["ups.info"] = ups_info
    ups_driver_info = Info(f"{METRIC_NAME_PREFIX}_ups_driver", "UPS driver metadata", ["ups"])
    service_metrics["ups.driver.info"] = ups_driver_info

    with nut["rpi5"].session() as session:
        ups_list = session.list_ups()
        for upsname in ups_list:
            ups_vars = session.list_vars(upsname)
            ups_info.labels(ups = f"{upsname}@{nut["rpi5"].host}").info(get_veriables(UPS_INFO_VARS, ups_vars))
            ups_driver_info.labels(ups = f"{upsname}@{nut["rpi5"].host}").info(get_veriables(UPS_DRIVER_INFO_VARS, ups_vars))
            init_metrics()

    while True:
        try:
            with nut["rpi5"].session() as session:
                ups_list = session.list_ups()
                for upsname in ups_list:
                    fetch_data(session, f"{upsname}@{nut["rpi5"].host}")
        except Exception as e:
            logging.exception(f"Failed to fetch data: {e}")
        time.sleep(5)
