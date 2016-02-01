
from gevent.wsgi import WSGIServer
from flask import Flask, render_template
from werkzeug.routing import BaseConverter

from utils import CONFIG

import services


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]

app = Flask(__name__)
app.url_map.converters['regex'] = RegexConverter


@app.route("/", methods=['GET'])
def landing(services=services):
    return render_template('landing.html', **services.get_projects())


@app.route('/<regex("[a-zA-Z0-9_]+"):id>:<regex("[0-9]+"):idx>', methods=['GET'])
def experiment(id, idx, services=services):
    idx = int(idx)
    return render_template('project.html', **services.get_project(id, idx))


if __name__ == "__main__":
    app.debug = True
    server = WSGIServer(("", CONFIG["app"]["server-port"]), app)
    server.serve_forever()
