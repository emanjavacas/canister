# coding: utf-8

import os
import logging
import inspect
import contextlib
from getpass import getuser
from platform import platform
from subprocess import check_output, CalledProcessError
from time import time
from uuid import uuid4
from tinydb import TinyDB, where


logger = logging.getLogger(__name__)


def log(msg, level=logging.INFO):
    logger.log(level, msg)


def get_commit(fname):
    if os.path.isfile(fname):
        dirname = os.path.dirname(fname)
    elif os.path.isdir(fname):
        dirname = fname
    else:
        log("Not valid path %s" % fname)
    try:
        commit = check_output(["git", "describe", "--always"], cwd=dirname)
        return commit.strip().decode('utf-8')
    except FileNotFoundError:
        log("Git doesn't seem to be installed in your system")
    except CalledProcessError:
        log("Not a git repository")


def make_hash(o):
    def freeze(o):
        if isinstance(o, dict):
            return frozenset({k: freeze(v) for k, v in o.items()}.items())
        if isinstance(o, list):
            return tuple([freeze(v) for v in o])
        return o
    return hash(freeze(o))


def merge(d1, d2):
    return dict(d1, **d2)


def append(field, item):
    def transform(element):
        if field not in element:
            element[field] = [item]
        else:
            element[field].append(item)
    return transform


def update_in(d, path, f, *args):
    if len(path) == 1:
        if callable(path[0]):
            assert isinstance(d, list), "Found pred but target is not list"
            for idx, i in enumerate(d):
                if path[0](i):
                    d[idx] = f(i, *args)
            raise KeyError("Pred failed at %s" % i)
        else:
            d[path[0]] = f(d.get(path[0]), *args)
    else:
        if callable(path[0]):
            assert isinstance(d, list), "Found pred but target is not list"
            for i in d:
                if path[0](i):
                    update_in(i, path[1:], f, *args)
            raise KeyError("Pred failed at %s" % i)
        else:
            if path[0] not in d:
                d[path[0]] = {}
            update_in(d[path[0]], path[1:], f, *args)


def append_in(path, item):
    def transform(element):
        update_in(element, path, lambda l: (l or []) + [item])
    return transform


def assign_in(path, item):
    def transform(element):
        update_in(element, path, lambda d: merge(d or {}, item))
    return transform


def extend(field, item):
    def transform(element):
        if field not in element:
            element[field] = [item]
        if isinstance(element[field], list):
            if item not in set(element[field]):
                element[field].append(item)
    return transform


def remove(field, item):
    def transform(element):
        if field not in element:
            return
        if isinstance(element[field], list):
            element[field] = [x for x in element[field] if x != item]
    return transform


def model_pred(model_id):
    def f(model):
        return model["model_id"] == model_id
    return f


def params_pred(params_hash):
    def f(results):
        return make_hash(results["params"]) == params_hash
    return f


class Experiment:
    def __init__(self, path):
        self.db = TinyDB(path)
        self.id = self.get_id()

    def get_id(self):
        return uuid4().hex

    def exists(self):
        return self.db.get(where("id") == self.id)

    @classmethod
    def new(cls, path, corpus, tags=(), **opt_params):
        exp = cls(path)
        if exp.exists():
            raise ValueError("Experiment %s already exists" % exp.id)
        base = {"id": exp.id,
                "corpus": corpus,
                "tags": tags,
                "created": time()}
        exp.db.insert(merge(base, opt_params))
        return exp

    @classmethod
    def use(cls, path, corpus, tags=(), **opt_params):
        exp = cls(path)
        if exp.exists():
            return exp
        else:
            log("Creating new Experiment %s" % exp.id)
            return cls.new(path, corpus, tags=tags, **opt_params)

    def add_tag(self, tag):
        self.db.update(
            extend("tags", tag), where("id") == self.id)

    def remove_tag(self, tag):
        return self.db.update(
            remove("tags", tag), where("id") == self.id)

    def getsourcefile(self):
        return os.path.realpath(inspect.getsourcefile(type(self)))

    def get_commit(self):
        return get_commit(self.getsourcefile())

    def find_model_by_key(self, key, val):
        return self.db.get((where("id") == self.id) &
                           where("models").any(where(key) == val))

    def get_model(self, model_id):
        return self.find_model_by_key("model_id", model_id)

    def model(self, model_id, model_config={}):
        return self.Model(self, model_id, model_config)

    class Model:
        def __init__(self, experiment, model_id, model_config={}):
            self.session_params = None
            self.experiment = experiment
            self.model_id = model_id
            self.cond = ((where("id") == experiment.id) &
                         where("models").any(where("model_id") == model_id))
            if not self.experiment.get_model(self.model_id):
                model = {"model_id": model_id, "model_config": model_config}
                self.experiment.db.update(
                    append_in(["models"], model),
                    where("id") == self.experiment.id)

        def result_meta(self):
            return {
                "commit": self.experiment.get_commit() or "not-git-tracked",
                "user": getuser(),
                "platform": platform(),
                "timestamp": time()}

        def check_params(self, params):
            models = self.experiment.db.search(
                where("id") == self.experiment.id)["models"]
            params_hash = make_hash(params)
            for model in models:
                if make_hash(model["params"]) == params_hash:
                    log("Model with input params already run")

        @contextlib.contextmanager
        def session(self, params):
            try:
                self.check_params(params)
                self.session_params = params
                result = {"params": params, "meta": self.result_meta()}
                which_model = model_pred(self.model_id)
                path = ["models", which_model, "results"]
                self.experiment.db.update(append_in(path, result), self.cond)
                yield self
            finally:
                self.session_params = None

        def _add_result(self, result, params):
            meta = self.result_meta()
            which_model = model_pred(self.model_id)
            result = {"params": params, "meta": meta, "result": result}
            path = ["models", which_model, "results"]
            self.experiment.db.update(append_in(path, result), self.cond)

        def _add_session_result(self, result):
            params_hash = make_hash(self.session_params)
            which_model = model_pred(self.model_id)
            which_result = params_pred(params_hash)
            path = ["models", which_model, "results", which_result, "result"]
            self.experiment.db.update(append_in(path, result), self.cond)

        def add_result(self, result, params=None):
            if not params and not self.session_params:
                raise ValueError("Experiment params missing")
            if not self.session_params:
                self._add_result(result, params)
            else:
                self._add_session_result(result)

        def add_epoch(self, epoch_num, result):
            if not self.session_params:
                raise ValueError("add_epoch requires session")
            result.update({"epoch_num": epoch_num})
            self._add_session_result(result)

# model = Experiment.use("test.json", "corpus").model("test-model")
# with model.session(params) as session:
#     session.add_result()
# db = TinyDB("test.json")
# model = Experiment.use("test.json", "corpus").model("test-model")
# model.add_result({"a": 1}, "good")
# db.insert({"a": {"b": "c", "d": {"A": "V"}}})
# q = Query("a")
# db.search(where("a")["d"]["A"] == "V")
# db.search(where("a").any())

# d = {"a": [{"b": [{"c": 1}]},
#            {"d": [{"e": 2}]}]}

# update_in(d, ["a", lambda x: "b" in x], lambda d: merge(d, {"Hu!": "Ha!"}))
# update_in(d, ["a", lambda x: "f" in x, "h"], lambda l: (l or []) + ["HI!"])
