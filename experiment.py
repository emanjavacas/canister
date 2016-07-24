# coding: utf-8

import os
import logging
import inspect
import contextlib
from datetime import datetime
from uuid import uuid4
from platform import platform
from getpass import getuser
from subprocess import check_output, CalledProcessError

from tinydb import TinyDB, where

from sftp_storage import SFTPStorage, WrongPathException


class ExistingModelParams(Exception):
    pass


logger = logging.getLogger(__name__)


def log(msg, level=logging.WARN):
    logger.log(level, msg)


def get_commit(fname):
    """Returns current commit on file specified by fname or None if an error
    is thrown by git (File doesn't exist) or if file is not under git VCS"""
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


def parse_date(string_date):
    """
    >>> now = datetime.now()
    >>> assert now == parse_date(str(now))
    """
    return datetime.strptime(string_date, "%Y-%m-%d %H:%M:%S.%f")


def make_hash(o):
    """Returns a hash number for an object, which can also be a dict or a list

    >>> make_hash(range(10))
    -6299899980521991026
    >>> make_hash(list(range(10)))
    -4181190870548101704
    >>> a = make_hash({'a': 1, 'b': 2, 'c': 3})
    >>> b = make_hash({'c': 3, 'a': 1, 'b': 2})
    >>> a == b
    True
    """
    def freeze(o):
        if isinstance(o, dict):
            return frozenset({k: freeze(v) for k, v in o.items()}.items())
        if isinstance(o, list):
            return tuple([freeze(v) for v in o])
        return o
    return hash(freeze(o))


def merge(d1, d2):
    """merges two dictionaries, nested values are overwitten by d1

    >>> d = merge({'a': 1}, {'b': 2})
    >>> assert d == {'a': 1, 'b': 2}

    >>> d = merge({'a': {'b': 2}}, {'b': 2, 'a': {'c': 3}})
    >>> assert d == {'a': {'c': 3}, 'b': 2}
    """
    return dict(d1, **d2)


def update_in(d, path, f, *args):
    """
    Parameters:
    -----------
    d: dict
    path: list of key or function
    f: update function (takes nested element or None if element isn't found)

    Applies func `f` on dict `d` on element nested specified by list `path`.
    Items in path are dictionary keys or functions. If a key doesn't match any
    element, an empty dictionary is created at that point. If a nested element
    is a list, the corresponding path item should be a pred func that takes a
    list and returns True at a desired item. If no element in list is matched,
    nothing else happens. If a pred match multiple elements, last one is used.

    # Normal nested update
    >>> d = {'c': {'d': 2}}
    >>> update_in(d, ['c', 'd'], lambda x: x + 3)
    >>> assert d == {'c': {'d': 5}}

    # Update on missing element
    >>> d = {'a': {'b': 1}}
    >>> update_in(d, ['c', 'd'], lambda x: x or [] + [3])
    >>> assert d == {'a': {'b': 1}, 'c': {'d': [3]}}

    # Update on dictionary inside nested list
    >>> d = {'a': [{'b': {'c': 1}}, {'d': 2}]}
    >>> update_in(d, ['a', lambda x: 'b' in x, 'b', 'c'], lambda x: x + 3)
    >>> assert d == {'a': [{'b': {'c': 4}}, {'d': 2}]}

    # Non update on failing pred
    >>> d = {'a': [{'b': {'c': 1}}, {'d': 2}]}
    >>> update_in(d, ['a', lambda x: 'e' in x, 'b', 'c'], lambda x: x + 3)
    >>> assert d == {'a': [{'b': {'c': 1}}, {'d': 2}]}

    # Update on first matchin element of list
    >>> d = {'a': [{'b': {'c': 1}}, {'d': 2}, {'b': {'c': 2}}]}
    >>> update_in(d, ['a', lambda x: 'b' in x, 'b', 'c'], lambda x: x + 3)
    >>> assert d == {'a': [{'b': {'c': 1}}, {'d': 2}, {'b': {'c': 5}}]}
    """
    if len(path) == 1:
        if callable(path[0]):
            assert isinstance(d, list), "Found pred but target is not list"
            for idx, i in list(enumerate(d))[::-1]:  # reverse list
                if path[0](i):
                    d[idx] = f(i, *args)
                    return
        else:
            d[path[0]] = f(d.get(path[0]), *args)
    else:
        if callable(path[0]):
            assert isinstance(d, list), "Found pred but target is not list"
            for i in d[::-1]:
                if path[0](i):
                    update_in(i, path[1:], f, *args)
                    break       # avoid mutating multiple instances
        else:
            if path[0] not in d:
                d[path[0]] = {}
            update_in(d[path[0]], path[1:], f, *args)

"""
TinyDB extra operations
"""


def append(field, item):
    def transform(element):
        if field not in element:
            element[field] = [item]
        else:
            element[field].append(item)
    return transform


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


"""
Factory update_in preds for models
"""


def model_pred(model_id):
    def f(model):
        return model["model_id"] == model_id
    return f


def params_pred(params):
    def f(result):
        return result["params"] == params
    return f


class Experiment:
    def __init__(self, path):
        try:
            self.db = TinyDB(path, policy='autoadd', storage=SFTPStorage)
        except WrongPathException:
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
            raise ValueError("Experiment %s already exists" % str(exp.id))
        base = {"id": exp.id,
                "corpus": corpus,
                "tags": tags,
                "created": str(datetime.now())}
        exp.db.insert(merge(base, opt_params))
        return exp

    @classmethod
    def use(cls, path, corpus, tags=(), **opt_params):
        exp = cls(path)
        if exp.exists():
            return exp
        else:
            log("Creating new Experiment %s" % str(exp.id))
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
            self._session_params = None
            self.session_id = uuid4().hex
            self.e = experiment
            self.model_id = model_id
            self.cond = ((where("id") == experiment.id) &
                         where("models").any(where("model_id") == model_id))
            if not self.e.get_model(self.model_id):
                model = {"model_id": model_id, "model_config": model_config}
                self.e.db.update(append_in(["models"], model),
                                 where("id") == self.e.id)

        def _result_meta(self):
            return {"commit": self.e.get_commit() or "not-git-tracked",
                    "user": getuser(),
                    "platform": platform(),
                    "timestamp": str(datetime.now())}

        def _check_params(self, params):
            ms = self.e.db.get(where("id") == self.e.id)["models"]
            model = next(m for m in ms if m if m["model_id"] == self.model_id)
            for result in model.get("sessions", []):
                if result["params"] == params:
                    raise ExistingModelParams()

        def _add_result(self, result, params):
            meta = self._result_meta()
            which_model = model_pred(self.model_id)
            result = {"params": params, "meta": meta, "result": result}
            path = ["models", which_model, "sessions"]
            self.e.db.update(append_in(path, result), self.cond)

        @contextlib.contextmanager
        def session(self, params, ensure_unique=True):  # to try: store on exit
            """
            Context manager for cases in which we want to add several results
            to the same experiment run. Current session is identified based on
            `params` (see _add_session_result)

            Parameters:
            -----------
            params: dict, parameters passed in to the model instance
            ensure_unique: bool, throw an exception in case model has already
                been run with the same parameters
            """
            if ensure_unique:
                self._check_params(params)
            # enter
            self._session_params = params
            result = {"params": params, "meta": self._result_meta()}
            path = ["models", model_pred(self.model_id), "sessions"]
            self.e.db.update(append_in(path, result), self.cond)
            yield self
            # exit
            self._session_params = None

        def _add_session_result(self, result):
            """
            Adds (partial) result to session currently running. Session is
            identifed based on session `params`. In case a model is run with
            the same params in a second session, results are added to the
            chronologically last session (which means that we relay on the fact
            that `update_in` checks lists in reverse, see `update_in`)
            """
            which_model = model_pred(self.model_id)
            which_result = params_pred(self._session_params)
            path = ["models", which_model, "sessions", which_result, "result"]
            self.e.db.update(append_in(path, result), self.cond)

        def add_result(self, result, params=None):
            if not params and not self._session_params:
                raise ValueError("Experiment params missing")
            if not self._session_params:
                self._add_result(result, params)
            else:
                self._add_session_result(result)

        def add_epoch(self, epoch_num, result, timestamp=True):
            if not self._session_params:
                raise ValueError("add_epoch requires session context manager")
            result.update({"epoch_num": epoch_num})
            if timestamp:
                result.update({"timestamp": str(datetime.now())})
            self._add_session_result(result)

# model = Experiment.use("test.json", "corpus").model("test-model")
# with model.session(params) as session:
#     session.add_result()
# db = TinyDB("test.json")
# db.all()
# model = Experiment.use("test.json", "corpus").model("test-model")
# model.add_result({"a": 1}, "good")
# db.insert({"a": {"b": "c", "d": {"A": "V"}}})
# q = Query("a")
# db.search(where("a")["d"]["A"] == "V")
# db.search(where("a").any())

if __name__ == '__main__':
    import doctest
    doctest.testmod()
