from flask import Flask, jsonify
from nutclient import NutClient
import logging
import yaml

logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] [%(name)s] %(message)s")

app = Flask(__name__)
nut = None

@app.route('/ups', methods=['GET'])
def ups_status():
    return jsonify(nut.list_ups())

@app.route('/ups/<upsname>/stats', methods=['GET'])
def ups_stats(upsname):
    return jsonify(nut.list_vars(upsname))
    
@app.route('/ups/<upsname>/stats/<variable>', methods=['GET'])
def ups_variable(upsname, variable):
    value = nut.get_var(upsname, variable)
    return jsonify({variable: value})

if __name__ == '__main__':
    with open('./config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    
    server_config = config['servers'][0]
    # Filter out the keys we want to pass to the NutClient
    filtered_config = {key: server_config[key] for key in ['host', 'port'] if key in server_config}
    nut = NutClient(**filtered_config)
    
    app.run(host='0.0.0.0', port=8080)