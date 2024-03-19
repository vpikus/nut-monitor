from flask import Flask, jsonify
from nutclient import NutClient
import logging.config
import yaml
import os

HOME_DIR = os.environ.get('NUT_API_HOME', os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = f"{HOME_DIR}/config"
LOG_DIR = os.environ.get('NUT_API_LOG_DIR', f"{HOME_DIR}/logs")

def setup_logging():
    with open(f"{CONFIG_DIR}/logging.yml", 'r') as file:
        config = yaml.safe_load(file.read())
    config['handlers']['file']['filename'] = f"{LOG_DIR}/nut-monitor-api.log"
    logging.config.dictConfig(config)

setup_logging()

app = Flask(__name__)
# I don't like strict slashes xD
app.url_map.strict_slashes = False

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

nut = load_config_and_initialize()

@app.route('/servers', methods=['GET'])
def get_servers():
    logging.debug("Getting list of servers")
    return jsonify(list(nut.keys()))

@app.route('/servers/<servername>/ups', methods=['GET'])
def list_ups(servername):
    return jsonify(nut[servername].list_ups())

@app.route('/servers/<servername>/ups/<upsname>/statistics', methods=['GET'])
def ups_statistics(servername, upsname):
    return jsonify(nut[servername].list_vars(upsname))

@app.route('/servers/<servername>/ups/<upsname>/variables/<variable>', methods=['GET'])
def ups_variable_val(servername, upsname, variable):
    value = nut[servername].get_var(upsname, variable)
    return jsonify({variable: value})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080)
