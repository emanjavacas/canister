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


class ExistingModelParamsException(Exception):
    pass


logger = logging.getLogger(__name__)


def log(msg, level=logging.WARN):
    logger.log(level, msg)


def get_dir(fname):
    if os.path.isfile(fname):
        return os.path.dirname(fname)
    elif os.path.isdir(fname):
        return fname
    else:
        raise ValueError("Not valid path %s" % fname)


class GitInfo:
    def __init__(self, fname):
        self.dirname = get_dir(fname)

    def run(self, cmd):
        try:
            output = check_output(cmd, cwd=self.dirname)
            return output.strip().decode('utf-8')
        except OSError:
            log("Git doesn't seem to be installed in your system")
        except CalledProcessError:
            log("Not a git repository")

    def get_commit(self):
        """
        Returns current commit on file or None if an error is thrown by git
        (OSError) or if file is not under git VCS (CalledProcessError)
        """
        return self.run(["git", "describe", "--always"])

    def get_branch(self):
        """
        Returns current active branch on file or None if an error is thrown
        by git (OSError) or if file is not under git VCS (CalledProcessError)
        """
        return self.run(["git", "rev-parse", "--abbrev-ref", "HEAD"])


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
            assert isinstance(d, list), "Found pred but target is %s" % type(d)
            for idx, i in list(enumerate(d))[::-1]:  # reverse list
                if path[0](i):
                    d[idx] = f(i, *args)
                    return
        else:
            d[path[0]] = f(d.get(path[0]), *args)
    else:
        if callable(path[0]):
            assert isinstance(d, list), "Found pred but target is %s" % type(d)
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


def extend_in(path, item):
    """
    Appends item to a list nested in the matching db entry specified by `path`
    """
    def transform(element):
        update_in(element, path, lambda l: (l or []) + [item])
    return transform


def assign_in(path, item):
    """
    Sets item to a dict nested in the matching db entry specified by `path`
    """
    def transform(element):
        update_in(element, path, lambda d: merge(d or {}, item))
    return transform


def extend(field, item):
    """
    Appends item to a list specified by `path` in the matching db entry
    """
    def transform(element):
        if field not in element:
            element[field] = [item]
        if isinstance(element[field], list):
            if item not in set(element[field]):
                element[field].append(item)
    return transform


def remove(field, item):
    """
    Removes item from list
    """
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
        return model["modelId"] == model_id
    return f


def params_pred(params):
    def f(result):
        return result["params"] == params
    return f


class Experiment:
    """
    A class to encapsulate information about a experiment and store
    together different experiment runs.
    The recommended way to identify an experiment is overwriting
    Experiment.get_id in a child class in a way that is dependent
    from the source file. Example:

    class MyExperiment(Experiment):
        def get_id(self):
            return inspect.getsourcefile(self)  # return __file__

    Alternatively, one can pass an id as a constructor parameter. If
    no id is passed, the default behaviour is to generate a random id
    (meaning a new experiment is created for each run).

    Experiments are instantiated with the classmethod Experiment.new,
    which additionally stores the experiment in the database with useful
    metadata or Experiment.use, which additionally makes sure that the
    experiment is stored only the first time.
    Actual experiments are run on models. To add a model to the current
    experiment, instantiate the inner class Model with Experiment.model.

    model = Experiment.use(path, corpus).model("modelId", {"type": "SVM"})

    Model instantiates and encapsulates model information, providing
    database persistency. A model_id is required to identify the model.
    It also provides convenience methods to store experiment results for
    both single-result and epoch-based training experiments.
    See Model.session

    Parameters:
    -----------
    path: str, path to the database file backend. A path in a remote
        machine can be specified with syntax:
        username@host:/path/to/remote/file.
    """
    def __init__(self, path, exp_id=None):
        try:
            from sftp_storage import SFTPStorage, WrongPathException
            try:
                self.db = TinyDB(path, policy='autoadd', storage=SFTPStorage)
            except WrongPathException:
                self.db = TinyDB(path)
        except ImportError:
            self.db = TinyDB(path)

        self.git = GitInfo(self.getsourcefile())
        self.id = exp_id if exp_id else self.get_id()

    def get_id(self):
        return uuid4().hex

    def getsourcefile(self):
        return os.path.realpath(inspect.getsourcefile(type(self)))

    def exists(self):
        return self.db.get(where("id") == self.id)

    def set_corpus(self, corpus):
        self.db.insert({"corpus": corpus})

    def add_tag(self, tag):
        self.db.update(
            extend("tags", tag), where("id") == self.id)

    def remove_tag(self, tag):
        return self.db.update(
            remove("tags", tag), where("id") == self.id)

    @classmethod
    def new(cls, path, corpus, exp_id=None, tags=(), **params):
        """
        Stores a new Experiment in the database. Throws an exception if
        experiment already exists.
        """
        exp = cls(path)
        if exp.exists():
            raise ValueError("Experiment %s already exists" % str(exp.id))
        base = {"id": exp_id if exp_id else exp.get_id(),
                "corpus": corpus,
                "tags": tags,
                "created": str(datetime.now())}
        exp.db.insert(merge(base, params))
        return exp

    @classmethod
    def use(cls, path, corpus, exp_id=None, tags=(), **params):
        """
        Only stores a new Experiment if none can be find with given parameters,
        otherwise instantiate the existing one with data from database.
        """
        exp = cls(path, exp_id=exp_id)
        if exp.exists():
            return exp
        else:
            log("Creating new Experiment %s" % str(exp.id))
            return cls.new(path, corpus, exp_id=exp_id, tags=tags, **params)

    def model_exists(self, model_id):
        """
        Returns:
        --------

        dict or None
        """
        return self.db.get((where("id") == self.id) &
                           where("models").any(where("modelId") == model_id))

    def model(self, model_id, model_config={}):
        return self.Model(self, model_id, model_config)

    class Model:
        def __init__(self, experiment, model_id, model_config={}):
            self._session_params = None
            self.e = experiment
            self.model_id = model_id
            self.which_model = model_pred(self.model_id)
            self.cond = ((where("id") == experiment.id) &
                         where("models").any(where("modelId") == model_id))
            if not self.e.model_exists(self.model_id):
                model = {"modelId": model_id, "modelConfig": model_config}
                self.e.db.update(extend_in(["models"], model),
                                 where("id") == self.e.id)

        def _result_meta(self):
            return {"commit": self.e.git.get_commit() or "not-git-tracked",
                    "branch": self.e.git.get_branch() or "not-git-tracked",
                    "user": getuser(),
                    "platform": platform(),
                    "timestamp": str(datetime.now())}

        def _check_params(self, params):
            ms = self.e.db.get(where("id") == self.e.id)["models"]
            model = next(m for m in ms if m if m["modelId"] == self.model_id)
            for result in model.get("sessions", []):
                if result["params"] == params:
                    raise ExistingModelParamsException()

        def _add_result(self, result, params):
            meta = self._result_meta()
            result = {"params": params, "meta": meta, "result": result}
            path = ["models", self.which_model, "sessions"]
            self.e.db.update(extend_in(path, result), self.cond)

        def _add_session_result(self, result):
            """
            Adds (partial) result to session currently running. Session is
            identifed based on session `params`. In case a model is run with
            the same params in a second session, results are added to the
            chronologically last session (which means that we relay on the fact
            that `update_in` checks lists in reverse, see `update_in`)
            """
            which_result = params_pred(self._session_params)
            path = ["models", self.which_model, "sessions", which_result, "result"]
            self.e.db.update(extend_in(path, result), self.cond)

        def _start_session(self, params):
            self._session_params = params
            path = ["models", self.which_model, "sessions"]
            result = {"params": params, "meta": self._result_meta()}
            self.e.db.update(extend_in(path, result), self.cond)

        def _end_session(self):
            self._session_params = None

        @contextlib.contextmanager
        def session(self, params, ensure_unique=True):  # to try: store on exit
            """
            Context manager for cases in which we want to add several results
            to the same experiment run. Current session is identified based on
            `params` (see _add_session_result).

            Example:
            model_db = Experiment.use("test.json", "test-corpus").model("id")
            with model_db.session({"param-1": 10, "param-2": 100}) as session:
                from time import time
                start_time = time()
                svm.fit(X_train, y_train)
                end_time = time()
                session.add_meta({"duration": end_time - start_time})
                y_pred = svm.predict(X_test)
                session.add_result({"accuracy": accuracy(y_pred, y_true)})

            Parameters:
            -----------
            params: dict, parameters passed in to the model instance
            ensure_unique: bool, throw an exception in case model has already
                been run with the same parameters
            """
            if ensure_unique:
                self._check_params(params)
            self._start_session(params)
            yield self
            self._end_session()

        def add_meta(self, d):
            """
            Parameters:
            -----------
            d: dict, Specifies multiple key-val additional info for the session
            """
            if not self._session_params:
                raise ValueError("add_meta requires session context manager")
            if not isinstance(d, dict):
                raise ValueError("add_meta input must be dict")
            which_result = params_pred(self._session_params)
            path = ["models", self.which_model, "sessions", which_result, "meta"]
            self.e.db.update(assign_in(path, d), self.cond)

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


if __name__ == '__main__':
    import doctest
    doctest.testmod()
