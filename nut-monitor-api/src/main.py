from flask import Flask, jsonify, request, Response, abort
from werkzeug.routing import BaseConverter
from werkzeug.exceptions import HTTPException
from nutclient import NutClient, NutAuthentication
import logging.config
import yaml
from http import HTTPStatus
from functools import wraps
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

def nut_auth(f):
    """
    Decorator to handle basic authentication for NUT API routes.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        nut_auth: NutAuthentication = None
        if auth:
            nut_auth = NutAuthentication(username=auth.username, password=auth.password)
        kwargs['auth'] = nut_auth
        # Pass the nut_auth model to the route function
        return f(*args, **kwargs)
    return decorated_function

class NutServerConverter(BaseConverter):
    def to_python(self, servername) -> NutClient:
        if servername not in nut:
            abort(404, description="Server not found")
        server = nut[servername]
        return server

    def to_url(self, servername):
        return super().to_url(servername)

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.url_map.converters['servername'] = NutServerConverter
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
    return 'OK', HTTPStatus.OK

@app.route('/servers', methods=['GET'])
def get_servers():
    return jsonify(list(nut.keys()))

@app.get('/servers/<servername:server>/tracking')
@nut_auth
def tracking(server: NutClient, auth: NutAuthentication):
    with server.session(auth) as session:
        return jsonify({"value": session.tracking()})

@app.patch('/servers/<servername:server>/tracking')
@nut_auth
def tracking_on_off(server: NutClient, auth: NutAuthentication):
    status = request.json['status'].upper()
    with server.session(auth) as session:
        if status == "ON":
            session.tracking_on()
            return HTTPStatus.OK
        elif status == "OFF":
            session.tracking_off()
            return HTTPStatus.OK
        else:
            return jsonify({"error": "Invalid status"}), HTTPStatus.BAD_REQUEST

@app.get('/servers/<servername:server>/ups')
@nut_auth
def list_ups(server: NutClient, auth: NutAuthentication):
    with server.session(auth) as session:
        return jsonify(session.list_ups())

@app.get('/servers/<servername:server>/ups/<upsname>')
@nut_auth
def ups(server: NutClient, auth: NutAuthentication, upsname: str):
    with server.session(auth) as session:
        return jsonify({
                "name": upsname,
                "description": session.ups_desc(upsname),
                "logins": session.num_logins(upsname),
                "clients": session.list_clients(upsname),
            })

@app.get('/servers/<servername:server>/ups/<upsname>/stats')
@nut_auth
def ups_statistics(server: NutClient, auth: NutAuthentication, upsname: str):
    with server.session(auth) as session:
        return jsonify(session.list_vars(upsname))

@app.get('/servers/<servername:server>/ups/<upsname>/vars')
@nut_auth
def list_vars(server: NutClient, auth: NutAuthentication, upsname: str):
    mode = request.args.get('type', type=str)
    vars = []
    with server.session(auth) as session:
        var_dict = session.list_vars(upsname) if mode != "rw" else session.list_rw_vars(upsname)
        for var in var_dict:
            vars.append({
                "name": var,
                "value": var_dict[var],
                "description": session.var_desc(upsname, var),
                "types": [it.serialize() for it in session.var_type(upsname, var)]
            })
    return jsonify(vars)

@app.get('/servers/<servername:server>/ups/<upsname>/vars/<variable>')
@nut_auth
def var(server: NutClient, auth: NutAuthentication, upsname: str, variable: str):
    with server.session(auth) as session:
        return jsonify({
            "value": session.var_value(upsname, variable),
            "description": session.var_desc(upsname, variable),
            "types": [it.serialize() for it in session.var_type(upsname, variable)]
        })

@app.patch('/servers/<servername:server>/ups/<upsname>/vars/<variable>')
@nut_auth
def set_var(server: NutClient, auth: NutAuthentication, upsname: str, variable: str):
    value = request.json['value']
    with server.session(auth) as session:
        session.set_var(upsname, variable, value)
        return Response(status=HTTPStatus.NO_CONTENT)

#
#@app.route('/servers/<servername:server>/ups/<upsname>/vars/<variable>/enum', methods=['GET'])
#def list_enum(servername, upsname, variable):
#    with server.session(auth) as session:
#        return jsonify(session.list_enum(upsname, variable))

#@app.route('/servers/<servername:server>/ups/<upsname>/vars/<variable>/range', methods=['GET'])
#def list_range(servername, upsname, variable):
#    with server.session(auth) as session:
#        return jsonify(session.list_range(upsname, variable))

@app.get('/servers/<servername:server>/ups/<upsname>/cmds')
@nut_auth
def list_cmds(server: NutClient, auth: NutAuthentication, upsname: str):
    cmds = []
    with server.session(auth) as session:
        for cmd in session.list_cmds(upsname):
            cmds.append({
                "name": cmd,
                "description": session.cmd_desc(upsname, cmd)
            })
    return jsonify(cmds)

@app.patch('/servers/<servername:server>/ups/<upsname>/cmds/<cmd>')
@nut_auth
def run_cmd(server: NutClient, auth: NutAuthentication, upsname: str, cmd: str):
    with server.session(auth) as session:
        value = request.json.get('value') if request.is_json else None
        session.run_cmd(upsname, cmd, *(value,) if value is not None else ())
        return Response(status=HTTPStatus.NO_CONTENT)

@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # Start with the correct headers and status code from the error
    response = e.get_response()
    # Replace the body with JSON
    response.data = jsonify({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    }).data
    response.content_type = "application/json"
    return response

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.DEBUG)

    app.run(host='127.0.0.1', port=8080)
