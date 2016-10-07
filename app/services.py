
from datetime import datetime
import json

from utils import CONFIG, flatten

from json2html import json2html


def transform(d, fn=lambda x: x or "null"):
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


def transform_layers(arch):
    "rearranges default keras config dictionary"
    def named_layers(layers):
        for idx, l in enumerate(layers):
            if 'name' in l:
                name = l['name']
                del l['name']
                yield name, l
    if 'layers' in arch:
        layers = arch['layers']
        arch['layers'] = dict(named_layers(layers))
    return arch


def dict2html(d):
    "wrapper over json2html, default to bootstrap"
    return json2html.convert(
        json=d, table_attributes=''.join(
            ['class="table table-bordered table-hover"',
             'style="list-style-type: none;font-size:small;"']))


def timestamp_to_str(timestamp):
    "parse timestamp"
    if isinstance(timestamp, basestring):
        timestamp = float(timestamp)
    timestamp = datetime.utcfromtimestamp(timestamp)
    return str(timestamp).split('.')[0]


def _handle_model(arch, fitted_model_idx):
    "returns a model dict for the fitted_model template"
    out = {}
    arch_params = arch['architecture_params']
    arch_params = dict2html(transform(transform_layers(arch_params)))
    fitted_model = dict(arch['fitted_models'][fitted_model_idx])
    epochs = fitted_model.pop('epochs')
    epochs = [e.result for e in epochs]
    timestamp = fitted_model.pop("timestamp")
    fitted_model_out = {}
    fitted_model_out['epochs'] = json.dumps(epochs)
    fitted_model_out['timestamp'] = timestamp_to_str(timestamp)
    fitted_model_out['params'] = dict2html(fitted_model)
    out['arch_name'] = arch['arch_name']
    out['arch_params'] = arch_params
    out['fitted_model'] = fitted_model_out
    out['model_id'] = timestamp
    return out


def _summarize_arch(arch):
    "returns a model dict for the model preview template"
    out = {}
    out_models = []
    fitted_models = enumerate(arch['fitted_models'])
    for idx, model in sorted(fitted_models, reverse=True,
                             key=lambda x: float(x[1]['timestamp'])):
        out_model = {}
        out_model['timestamp'] = timestamp_to_str(model["timestamp"])
        out_model['idx'] = idx
        out_models.append(out_model)
    arch_summary = {"Description":
                    arch.get("description", "No description available")}
    if arch["architecture_params"]:
        arch_params = arch["arch_params"]
        arch_summary["Model Type"] = arch_params["name"]
        arch_summary["Layers"] = [l['name'] for l in arch_params['layers']]
    out["corpus"] = arch["corpus"]
    out["tags"] = arch['tags']
    out["architecture_name"] = arch["arch_name"]
    out["fitted_models"] = out_models
    out["architecture_summary"] = dict2html(arch_summary)
    return out


def get_tags(mb=None):
    mb = ModelBase(CONFIG["db"]["db-path"]) if not mb else mb
    return set(flatten([a['tags'] for a in mb.get_archs()]))


def get_last_timestamp(mb=None):
    mb = ModelBase(CONFIG["db"]["db-path"]) if not mb else mb
    timestamps = list(flatten([float(m['timestamp'])
                               for a in mb.get_archs()
                               for m in a['fitted_models']]))
    return timestamp_to_str(sorted(timestamps)[0])


def get_arch(arch_name, corpus, fitted_model_idx, **kwargs):
    mb = ModelBase(CONFIG["db"]["db-path"])
    arch = mb.get_arch(arch_name, corpus, **kwargs)
    return _handle_model(arch, fitted_model_idx)


def get_experiments(tags=[]):
    mb = ModelBase(CONFIG["db"]["db-path"])
    if not tags:
        tags = get_tags(mb=mb)
    print(tags)
    archs = mb.get_archs({"tags": {"$in": ["unknown"]}})
    if not archs:               # todo: empty result from tag set filter
        return []
    return {"archs": [_summarize_arch(arch) for arch in archs],
            "n_projects": len(archs),
            "n_experiments": sum(len(arch['fitted_models']) for arch in archs),
            "last_timestamp": get_last_timestamp(mb=mb)}
