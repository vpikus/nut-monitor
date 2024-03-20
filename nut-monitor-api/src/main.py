from flask import Flask, jsonify, request
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

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/servers', methods=['GET'])
def get_servers():
    return jsonify(list(nut.keys()))

@app.route('/servers/<servername>/ups', methods=['GET'])
def list_ups(servername):
    return jsonify(nut[servername].list_ups())

@app.route('/servers/<servername>/ups/<upsname>/logins', methods=['GET'])
def ups_num_logins(servername, upsname):
    value = nut[servername].ups_num_logins(upsname)
    return jsonify({"value": value})

@app.route('/servers/<servername>/ups/<upsname>/description', methods=['GET'])
def ups_description(servername, upsname):
    value = nut[servername].ups_desc(upsname)
    return jsonify({"value": value})

@app.route('/servers/<servername>/ups/<upsname>/statistics', methods=['GET'])
def ups_statistics(servername, upsname):
    return jsonify(nut[servername].list_vars(upsname))

@app.route('/servers/<servername>/ups/<upsname>/variables', methods=['GET'])
def list_vars(servername, upsname):
    rw = request.args.get('rw', False, type=bool)
    var_dict = nut[servername].list_vars(upsname) if not rw else nut[servername].list_rw_vars(upsname)
    vars = []
    for var in var_dict:
        vars.append({
            "name": var,
            "value": var_dict[var],
            "description": nut[servername].var_desc(upsname, var),
            "type": nut[servername].var_type(upsname, var)
        })
    return jsonify(vars)

@app.route('/servers/<servername>/ups/<upsname>/variables/<variable>', methods=['GET'])
def var(servername, upsname, variable):
    value = nut[servername].var_value(upsname, variable)
    description = nut[servername].var_desc(upsname, variable)
    type = nut[servername].var_type(upsname, variable)
    return jsonify({
        "value": value,
        "description": description,
        "type": type
    })

@app.route('/servers/<servername>/ups/<upsname>/variables/<variable>/enum', methods=['GET'])
def list_enum(servername, upsname, variable):
    return jsonify(nut[servername].list_enum(upsname, variable))

@app.route('/servers/<servername>/ups/<upsname>/variables/<variable>/range', methods=['GET'])
def list_range(servername, upsname, variable):
    return jsonify(nut[servername].list_range(upsname, variable))

@app.route('/servers/<servername>/ups/<upsname>/cmds', methods=['GET'])
def list_cmds(servername, upsname):
    return jsonify(nut[servername].list_cmds(upsname))

@app.route('/servers/<servername>/ups/<upsname>/cmds/<cmd>', methods=['GET'])
def cmd(servername, upsname, cmd):
    description = nut[servername].cmd_desc(upsname, cmd)
    return jsonify({
        "description": description
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080)
