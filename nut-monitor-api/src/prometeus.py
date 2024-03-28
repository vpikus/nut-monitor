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
UPS_ALARM_KEY = "ups.alarm"
UPS_ALARM_NO_STATE = 0
UPS_ALARM_YES_STATE = 1
BTR_CHRG_STAT_KEY = "battery.charger.status"
UPS_STATUS_KEY = "ups.status"
UPS_POWER_KEY = "ups.power"

nut: dict[str, NutClient] = load_config_and_initialize()

service_metrics: Dict[str, Union[Gauge, Enum, Info]] = {
    UPS_ALARM_KEY: Gauge(f"{METRIC_NAME_PREFIX}_ups_alarm", "UPS alarm status", ["ups", "alarm"])
}

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
    UPS_POWER_KEY: {
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

UPS_ALARM_STATES = [
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

CHARGER_STATUS_LEGACY_TO_NEW = {
    "CHRG": "charging",
    "DISCHRG": "discharging"
}

enum_metric_config = {
    "ups.beeper.status": {
        "description": "UPS beeper status (enabled, disabled or muted)",
        "states": [
            "disabled",
            "enabled",
            "muted" # Temporarily muted
        ]
    },
    UPS_STATUS_KEY: {
        "description": "UPS status",
        "states": [
            "OFF", # UPS is offline and is not supplying power to the load
            "OL", # On line (mains is present)
            "OB" # On battery (mains is not present)
        ]
    },
    BTR_CHRG_STAT_KEY: {
        "description": "Battery charger status",
        "states": [
            "resting", # the battery is fully charged, and not charging nor discharging
            "charging", # battery is charging
            "discharging", # battery is discharging
            "floating", # battery has completed its charge cycle, and waiting to go to resting mode
        ]
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

def unwrap_legacy_ups_status(statistics: Dict[str, str]):
    original_status = statistics[UPS_STATUS_KEY]
    parts = original_status.split(" ")

    if parts[0] == "ALARM":
        alarm_type = parts[-1]  # Assuming the last part is the alarm type
        if UPS_ALARM_KEY in statistics:
            statistics[UPS_ALARM_KEY] += " " + alarm_type
            logging.warn(f"Ambiguous alarm status. Probably it's not configured correctly:\n\t{UPS_STATUS_KEY} = {original_status}\n\t{UPS_ALARM_KEY} = {statistics[UPS_ALARM_KEY]}")
        else:
            statistics[UPS_ALARM_KEY] = alarm_type
        parts = parts[1:-1]  # Remove the ALARM part and the alarm type

    if parts:
        statistics[UPS_STATUS_KEY] = parts[0]
    else:
        logging.error("Missing UPS status after processing ALARM. Check UPS status configuration.")
        return

    if len(parts) > 1:
        legacy_battery_status = parts[1]
        battery_status = CHARGER_STATUS_LEGACY_TO_NEW.get(legacy_battery_status, "resting")
        if BTR_CHRG_STAT_KEY in statistics and statistics[BTR_CHRG_STAT_KEY] != battery_status:
            logging.warning(f"Ambiguous battery charger status. The system might not be configured correctly:\n\t{UPS_STATUS_KEY} = {original_status}\n\t{BTR_CHRG_STAT_KEY} = {statistics[BTR_CHRG_STAT_KEY]}")
        statistics[BTR_CHRG_STAT_KEY] = battery_status
    elif BTR_CHRG_STAT_KEY not in statistics:
        # If the battery status is not present, assume it's resting
        statistics[BTR_CHRG_STAT_KEY] = "resting"

def calculate_ups_power(statistics: Dict[str, str]):
    if UPS_POWER_KEY in statistics:
        return

    try:
        load_pct = int(statistics.get("ups.load"))
        real_power_nominal = int(statistics.get("ups.realpower.nominal"))
        power = real_power_nominal * load_pct / 100
    except ValueError:
        power = 0

    statistics[UPS_POWER_KEY] = str(power)

def fetch_data(session: NutSession, ups: str):
    upsname, _ = ups.split("@")
    statistics = session.list_vars(upsname)
    calculate_ups_power(statistics)

    for varname, config in gauge_metric_config.items():
        value = statistics.get(varname)
        if value is not None:
            try:
                value = config["value-type"](value)
                service_metrics[varname].labels(ups=ups).set(value)
            except Exception:
                logging.exception(f"Failed to set value for {varname} with value '{value}'")

    unwrap_legacy_ups_status(statistics)

    try:
        alarm = statistics.get(UPS_ALARM_KEY)
        alarm_state = UPS_ALARM_NO_STATE if alarm is None else UPS_ALARM_YES_STATE
        service_metrics[UPS_ALARM_KEY].labels(ups=ups, alarm=alarm).set(alarm_state)
    except Exception:
        logging.exception(f"Failed to set value for {UPS_ALARM_KEY} with value '{alarm}'")

    for varname, config in enum_metric_config.items():
        value = statistics.get(varname)
        if value is not None:
            try:
                service_metrics[varname].labels(ups=ups).state(value)
            except Exception:
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

    start_http_server(NUT_PROMETEUS_PORT)

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
