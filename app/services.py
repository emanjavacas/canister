
from datetime import datetime
import json

from utils import CONFIG
from canister.storage import Model

from blitzdb import FileBackend
from json2html import json2html

backend = FileBackend(CONFIG["db"]["db-path"])


def lookup(d, key, *keys):
    if keys:
        return lookup(d.get(key, {}), *keys)
    return d.get(key)


def transform(d, fn):
    for k, v in d.iteritems():
        d[k] = fn(v)
        if isinstance(v, dict):
            transform(v, fn)
        if isinstance(v, list):
            for idx, vv in enumerate(v):
                if isinstance(vv, dict):
                    transform(vv, fn)
                else:
                    d[k][idx] = fn(vv)


def transform_layers(model):
    def named_layers(layers):
        for idx, l in enumerate(layers):
            if 'name' in l:
                name = l['name']
                del l['name']
                yield name, l

    if 'layers' in model:
        layers = model['layers']
        model['layers'] = dict(named_layers(layers))
    return model


def dict2html(d):
    return json2html.convert(
        json=d,
        table_attributes=''.join(
            ['class="table table-bordered table-hover"',
             'style="list-style-type: none;font-size:small;"']
        )
    )


def timestamp_to_str(s):
    date = datetime.utcfromtimestamp(float(s))
    return str(date).split('.')[0]


def handle_project(p, exp_id):
    experiment = p['experiments'][exp_id]
    experiment['date'] = timestamp_to_str(experiment.timestamp)
    experiment['params'] = dict2html(experiment['params'])
    experiment['epochs'] = json.dumps(dict(experiment['epochs']))
    p['architecture'] = dict2html(transform_layers(p['architecture']))
    p['experiment'] = experiment
    return p


def summarize_project(p):
    for idx, e in enumerate(p['experiments']):
        date = timestamp_to_str(e.timestamp)
        p['experiments'][idx]['idx'] = idx
        p['experiments'][idx]['date'] = date
    arch = {"Layers": [l['name'] for l in p['architecture']['layers']],
            "Model Type": p["architecture"]["name"],
            "Description": p.get("description", "")}
    p["architecture"] = dict2html(arch)
    return p


def get_project(model_id, exp_id):
    project = backend.get(Model, {'model_id': model_id})
    return handle_project(project, exp_id)


def get_projects():
    projects = backend.filter(Model, {})
    return {"projects": [summarize_project(p) for p in projects],
            "n_projects": len(projects),
            "n_experiments": sum(len(p['experiments']) for p in projects)}
