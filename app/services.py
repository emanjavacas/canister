
from datetime import datetime
import json

from utils import CONFIG
from canister.storage import Model

from blitzdb import FileBackend
from json2html import json2html

def transform(d, fn=lambda x: "null" if not x else x):
    "applies a transform function over the elements of nested iterables"
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
    return d


def transform_layers(model):
    "rearranges default keras config dictionary"
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
    "wrapper over json2html, default to bootstrap"
    return json2html.convert(
        json=d,
        table_attributes=''.join(
            ['class="table table-bordered table-hover"',
             'style="list-style-type: none;font-size:small;"']
        )
    )


def timestamp_to_str(s):
    "parse timestamp"
    date = datetime.utcfromtimestamp(float(s))
    return str(date).split('.')[0]


def _handle_project(p, exp_id):
    "returns a model dict for the project template"
    architecture = p['architecture']
    architecture = dict2html(transform(transform_layers(architecture)))
    p['architecture'] = architecture
    experiment = p['experiments'][exp_id]
    experiment['date'] = timestamp_to_str(experiment.timestamp)
    experiment['params'] = dict2html(experiment['params'])
    experiment['epochs'] = json.dumps(dict(experiment['epochs']))
    p['experiment'] = experiment
    return p


def _summarize_project(p):
    "returns a model dict for the model preview template"
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
    backend = FileBackend(CONFIG["db"]["db-path"])
    project = backend.get(Model, {'model_id': model_id})
    return _handle_project(project, exp_id)


def get_projects():
    backend = FileBackend(CONFIG["db"]["db-path"])
    projects = list(backend.filter(Model, {}))
    print projects
    return {"projects": [_summarize_project(p) for p in projects],
            "n_projects": len(projects),
            "n_experiments": sum(len(p['experiments']) for p in projects)}
