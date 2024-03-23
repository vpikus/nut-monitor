from flask import Flask, jsonify, request
import json
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
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
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

nut: dict[str, NutClient] = load_config_and_initialize()

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/servers', methods=['GET'])
def get_servers():
    return jsonify(list(nut.keys()))

@app.route('/servers/<servername>/tracking', methods=['GET'])
def tracking(servername):
    with nut[servername].session() as session:
        return jsonify({"value": session.tracking()})

@app.route('/servers/<servername>/tracking', methods=['PATCH'])
def tracking_on_off(servername):
    status = request.json['status'].upper()
    with nut[servername].session() as session:
        if status == "ON":
            session.tracking_on()
            return 200
        elif status == "OFF":
            session.tracking_off()
            return 200
        else:
            return jsonify({"error": "Invalid status"}), 400

@app.route('/servers/<servername>/ups', methods=['GET'])
def list_ups(servername):
    with nut[servername].session() as session:
        return jsonify(session.list_ups())

@app.route('/servers/<servername>/ups/<upsname>', methods=['GET'])
def ups(servername, upsname):
    with nut[servername].session() as session:
        return jsonify({
                "name": upsname,
                "description": session.ups_desc(upsname),
                "logins": session.num_logins(upsname),
                "clients": session.list_clients(upsname),
            })

@app.route('/servers/<servername>/ups/<upsname>/stats', methods=['GET'])
def ups_statistics(servername, upsname):
    with nut[servername].session() as session:
        return jsonify(session.list_vars(upsname))

@app.route('/servers/<servername>/ups/<upsname>/vars', methods=['GET'])
def list_vars(servername, upsname):
    mode = request.args.get('type', type=str)
    vars = []
    with nut[servername].session() as session:
        var_dict = session.list_vars(upsname) if mode != "rw" else session.list_rw_vars(upsname)
        for var in var_dict:
            vars.append({
                "name": var,
                "value": var_dict[var],
                "description": session.var_desc(upsname, var),
                "types": [it.serialize() for it in session.var_type(upsname, var)]
            })
    return jsonify(vars)

@app.route('/servers/<servername>/ups/<upsname>/vars/<variable>', methods=['GET'])
def var(servername, upsname, variable):
    with nut[servername].session() as session:
        return jsonify({
            "value": session.var_value(upsname, variable),
            "description": session.var_desc(upsname, variable),
            "types": [it.serialize() for it in session.var_type(upsname, variable)]
        })

@app.route('/servers/<servername>/ups/<upsname>/vars/<variable>', methods=['PATCH'])
def set_var(servername, upsname, variable):
    value = request.json['value']
    with nut[servername].session() as session:
        session.set_var(upsname, variable, value)
        return 200

#
#@app.route('/servers/<servername>/ups/<upsname>/vars/<variable>/enum', methods=['GET'])
#def list_enum(servername, upsname, variable):
#    with nut[servername].session() as session:
#        return jsonify(session.list_enum(upsname, variable))

#@app.route('/servers/<servername>/ups/<upsname>/vars/<variable>/range', methods=['GET'])
#def list_range(servername, upsname, variable):
#    with nut[servername].session() as session:
#        return jsonify(session.list_range(upsname, variable))

@app.route('/servers/<servername>/ups/<upsname>/cmds', methods=['GET'])
def list_cmds(servername, upsname):
    cmds = []
    with nut[servername].session() as session:
        for cmd in session.list_cmds(upsname):
            cmds.append({
                "name": cmd,
                "description": session.cmd_desc(upsname, cmd)
            })
    return jsonify(cmds)

@app.route('/servers/<servername>/ups/<upsname>/cmds/<cmd>', methods=['PATCH'])
def run_cmd(servername, upsname, cmd):
    value = request.json['value']
    with nut[servername].session() as session:
        session.run_cmd(upsname, cmd, value)
        return 200

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.DEBUG)

    app.run(host='127.0.0.1', port=8080)
