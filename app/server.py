
import json
from collections import defaultdict

import gevent
from gevent.wsgi import WSGIServer
from gevent.queue import Queue
from flask import Flask, render_template, request
from flask import Response, session, jsonify, url_for

from utils import CONFIG, SSE, RegexConverter

import services

app = Flask(__name__)
app.url_map.converters['r'] = RegexConverter
app.secret_key = CONFIG['secret_key']
subscriptions = defaultdict(list)

"""
Routes
"""


@app.route("/", methods=['GET'])
def landing(services=services):
    session_tags = session.get('tags', [])
    base_tags = services.get_tags()
    archs = services.get_archs(tags=session_tags)
    if not archs:
        return render_template('no_archs.html')
    return render_template('landing.html',
                           base_tags=base_tags,
                           session_tags=session_tags,
                           **archs)


@app.route("/tags", methods=['POST'])
def tags(services=services):
    action = request.form.get('action')
    new_tag = request.form.get('tag')
    old_tags = session.get('tags', [])
    if action == 'add':
        session['tags'] = [new_tag] + old_tags
    elif action == 'remove':
        session['tags'] = list(set(old_tags) - set([new_tag]))
    return jsonify({"endpoint": url_for("landing")})


arch_name_route = '/<r("[a-zA-Z0-9_ ]+"):arch_name>'
epoch_number_route = '<r("[0-9]+"):epoch_number>'
corpus_route = '<r(".*"):corpus>'
arch_route = '_'.join([arch_name_route, epoch_number_route, corpus_route])


@app.route(arch_route, methods=['GET'])
def experiment(arch_name, epoch_number, corpus, services=services):
    arch = services.get_arch(arch_name, "generated", int(epoch_number))
    return render_template('project.html', **arch)


@app.route("/publish/epoch/end/", methods=['POST'])
def publish_epoch():
    data = request.form.get('data')
    try:
        json.loads(data)
    except Exception as e:
        app.logger.error('Parsing error in /publish/epoch/end/: ' + str(e))
        return {'error': 'invalid data'}

    def notify():
        for sub in subscriptions["epoch"][:]:
            sub.put(data)

    gevent.spawn(notify)
    return "OK"


@app.route("/subscribe/epoch/end/")
def subscribe_epoch():
    def subscription_queue():
        q = Queue()
        subscriptions["epoch"].append(q)
        try:
            while True:
                epoch_data = q.get()
                event = SSE(data=epoch_data, event='epoch')
                yield event.encode()
        except GeneratorExit:
            subscriptions["epoch"].remove(q)
    return Response(subscription_queue(), mimetype="text/event-stream")


@app.route("/publish/train/", methods=['POST'])
def publish_train():
    data = request.form.get('data')
    try:
        json.loads(data)
    except Exception:
        app.logger.error('Parsing error in /publish/train/ ' + str(data))
        return {'error': 'invalid data'}

    def notify():
        for sub in subscriptions['train'][:]:
            sub.put(data)

    gevent.spawn(notify)
    return "OK"


@app.route("/subscribe/train/")
def subscribe_train():
    def subscription_queue():
        q = Queue()
        subscriptions["train"].append(q)
        try:
            while True:
                msg = q.get()
                event = SSE(data=msg, event='train')
                yield event.encode()
        except GeneratorExit:
            subscriptions["train"].remove(q)
    return Response(subscription_queue(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.debug = True
    server = WSGIServer(("", CONFIG["app"]["server-port"]), app)
    server.serve_forever()
