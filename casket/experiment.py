# coding: utf-8

import contextlib
import logging
from datetime import datetime
from uuid import uuid4
from platform import platform
from getpass import getuser

from tinydb import TinyDB, where

from . import utils
from .git import GitInfo


logger = logging.getLogger(__name__)


def log(msg, level=logging.NOTSET):
    logger.log(level, msg)


class ExistingModelParamsException(Exception):
    pass


"""
TinyDB extra operations
"""


def append(field, item):
    """
    Appends item to a list at value `field`
    """
    def transform(element):
        if field not in element:
            element[field] = [item]
        else:
            element[field].append(item)
    return transform


def append_in(path, item):
    """
    Appends item to a list nested in the matching db entry specified by `path`
    """
    def transform(element):
        utils.update_in(element, path, lambda l: (l or []) + [item])
    return transform


def assign_in(path, item):
    """
    Sets item to a dict nested in the matching db entry specified by `path`
    """
    def transform(element):
        utils.update_in(element, path, lambda d: utils.merge(d or {}, item))
    return transform


def extend(field, item):
    """
    Appends item to a set specified by `path` in the matching db entry
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

    model = Experiment.use(path).model("modelId", {"type": "SVM"})

    Model instantiates and encapsulates model information, providing
    database persistency. A model_id is required to identify the model.
    It also provides convenience methods to store experiment results for
    both single-result and epoch-based training experiments.
    See Model.session

    Parameters:
    -----------
    path : str
        Path to the database file backend. A path in a remote machine can
        be specified with syntax: username@host:/path/to/remote/file.
    """
    def __init__(self, path, exp_id=None, verbose=False):
        assert path, "Path cannot be the empty string"
        self.level = logging.WARN if verbose else logging.NOTSET
        try:
            from sftp_storage import SFTPStorage, WrongPathException
            try:
                self.db = TinyDB(path, policy='autoadd', storage=SFTPStorage)
                log("Using remote db file [%s]" % path, level=self.level)
            except WrongPathException:
                self.db = TinyDB(path)
        except:
            self.db = TinyDB(path)
            log("Using local file [%s]" % path, level=self.level)

        self.git = GitInfo(self.getsourcefile())
        self.id = exp_id if exp_id else self.get_id()

    def get_id(self):
        return uuid4().hex

    def getsourcefile(self):
        return utils.getsourcefile(lambda: None)

    def exists(self):
        return self.db.get(where("id") == self.id)

    def add_tag(self, tag):
        self.db.update(extend("tags", tag), where("id") == self.id)

    def remove_tag(self, tag):
        return self.db.update(remove("tags", tag), where("id") == self.id)

    def get_models(self):
        experiment = self.db.get(where("id") == self.id)
        return experiment.get("models") if experiment else {}

    @classmethod
    def new(cls, path, exp_id=None, tags=(), **params):
        """
        Stores a new Experiment in the database. Throws an exception if
        experiment already exists.
        """
        exp = cls(path, exp_id=exp_id)
        if exp.exists():
            raise ValueError("Experiment %s already exists" % str(exp.id))
        now, exp_id = str(datetime.now()), exp_id or exp.id
        base = {"id": exp_id, "tags": tags, "models": [], "created": now}
        exp.db.insert(utils.merge(base, params))
        return exp

    @classmethod
    def use(cls, path, exp_id=None, tags=(), **params):
        """
        Stores a new Experiment if none can be found with given parameters,
        otherwise instantiate the existing one with data from database.
        """
        exp = cls(path, exp_id=exp_id)
        if exp.exists():
            return exp
        else:
            log("Creating new Experiment %s" % str(exp.id))
            return cls.new(path, exp_id=exp_id, tags=tags, **params)

    def model_exists(self, model_id):
        """
        Returns:
        --------
        dict or None
        """
        return self.db.get(
            (where("id") == self.id) &
            where("models").any(where("modelId") == model_id))

    def model(self, model_id, model_config={}):
        return self.Model(self, model_id, {"config": model_config})

    class Model:
        def __init__(self, experiment, model_id, model_config):
            self._session_params = None
            self.e = experiment
            self.model_id = model_id
            self.which_model = model_pred(self.model_id)
            self.cond = ((where("id") == experiment.id) &
                         where("models").any(where("modelId") == model_id))
            if not self.exists():
                self._add_default_model(**model_config)

        def _add_default_model(self, **kwargs):
            model = utils.merge({"modelId": self.model_id}, kwargs)
            self.e.db.update(append("models", model), where("id") == self.e.id)

        def _result_meta(self):
            return {"commit": self.e.git.get_commit() or "not-git-tracked",
                    "branch": self.e.git.get_branch() or "not-git-tracked",
                    "user": getuser(),
                    "platform": platform(),
                    "timestamp": str(datetime.now())}

        def _check_params(self, params):
            models = self.e.get_models()
            if not models:
                return
            model = next(m for m in models if m["modelId"] == self.model_id)
            for result in model.get("sessions", []):
                if result["params"] == params:
                    raise ExistingModelParamsException()

        def _add_result(self, result, params):
            """
            Add session result (new)
            """
            meta = self._result_meta()
            result = {"params": params, "meta": meta, "result": result}
            path = ["models", self.which_model, "sessions"]
            self.e.db.update(append_in(path, result), self.cond)

        def _add_session_result(self, result, index_by=None):
            """
            Adds (partial) result to session currently running. Session is
            identifed based on session `params`. In case a model is run with
            the same params in a second session, results are added to the
            chronologically last session (which means that we relay on the fact
            that `update_in` checks lists in reverse, see `update_in`)

            Parameters:
            -----------
            result : (serializable-)dict

            index_by : serializable, optional
                Key to store result by.
                `result` is appended to session.result.index_by if given,
                or to session.result otherwise.
            """
            which_session = params_pred(self._session_params)
            path = ["models", self.which_model, "sessions", which_session,
                    "result"] + ([index_by] or [])
            self.e.db.update(append_in(path, result), self.cond)

        def _start_session(self, params):
            self._session_params = params
            path = ["models", self.which_model, "sessions"]
            result = {"params": params, "meta": self._result_meta()}
            self.e.db.update(append_in(path, result), self.cond)

        def _end_session(self):
            self._session_params = None

        def exists(self):
            return self.e.model_exists(self.model_id)

        @contextlib.contextmanager
        def session(self, params, ensure_unique=True):  # TODO: store on exit
            """
            Context manager for cases in which we want to add several results
            to the same experiment run. Current session is identified based on
            `params` (see _add_session_result).

            Example:
            model_db = Experiment.use("test.json").model("id")
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
            assert isinstance(params, dict), \
                "Params expected dict but got %s" % str(type(params))
            if ensure_unique:
                self._check_params(params)
            self._start_session(params)
            yield self
            self._end_session()

        def add_meta(self, d):
            """
            Adds session meta info

            Parameters:
            -----------
            d: dict, Specifies multiple key-val additional info for the session
            """
            if not self._session_params:
                raise ValueError("add_meta requires session context manager")
            if not isinstance(d, dict):
                raise ValueError("add_meta input must be dict")
            if not self.exists():
                self._add_default_model()
            which_session = params_pred(self._session_params)
            path = ["models", self.which_model, "sessions", which_session,
                    "meta"]
            self.e.db.update(assign_in(path, d), self.cond)

        def add_result(self, result, params=None, index_by=None):
            """
            appends result to models.$.sessions.$.result
            """
            if not params and not self._session_params:
                raise ValueError("Experiment params missing")
            if not self._session_params:
                self._add_result(result, params)
            else:
                self._add_session_result(result, index_by=index_by)

        def add_epoch(self, epoch_num, result, timestamp=True):
            if not self._session_params:
                raise ValueError("add_epoch requires session context manager")
            result.update({"epoch_num": epoch_num})
            if timestamp:
                result.update({"timestamp": str(datetime.now())})
            self._add_session_result(result, index_by="epochs")


if __name__ == '__main__':
    import doctest
    doctest.testmod()
