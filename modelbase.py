#!/usr/bin/python
# -*- coding: utf-8 -*-

from blitzdb import FileBackend
from blitzdocuments import FittedModel, Architecture, Epoch, PreferredParams


class ModelBase(object):
    """
    Defines connection to the backend
    Parameters
    ----------
    path: str
        path to FileBackend root

    local: boolean, optional, default True
        wether to use a FileBackend or not
    """
    def __init__(self, path, local=True):
        self.path = path
        self.local = local
        self._reconnect()

    def _reconnect(self):
        "needed in orted to keep in sync with the db"
        if self.local:
            self.db = FileBackend(self.path, config={"autocommit": True})
        else:
            raise NotImplementedError("Mongo not supported yet")

    def addresult(self, arch_name, corpus, params, result, model_id=None,
                  epoch_number=0, arch_params={}, tags=('unknown',)):
        """
        Adds a fitted model plus associated results to a given architecture
        Parameters
        ----------
        arch_name: str
            (Unique?) Architecture identifier

        corpus: str
            Corpus used in the experiments

        params: dict (JSON-serializable)
            Experiment params

        result: dict (JSON-serializable)
            Output of the experiment

        model_id: str/int/float, optional, default None
            fitted_model id to add the result to. If `None` a new model
            is created.

        epoch_number: int, optional, default 0
            Self-explaining

        arch_params: dict (JSON-serializable), optional, default {}
            Fixed architecture parameters to will be used across a experiments

        tags: tuple, optional, default ('unknown',)
        """
        self._reconnect()
        try:
            arch = self.db.get(Architecture,
                               {"architecture_name": arch_name,
                                "corpus": corpus})
        except Architecture.DoesNotExist:
            print("Couldn't find architecture")
            arch = Architecture({"architecture_name": arch_name,
                                 "architecture_params": arch_params,
                                 "corpus": corpus,
                                 "fitted_models": [],
                                 "preferred_params": {},
                                 "tags": tags})
        # fetch model
        model = self.getfitted(model_id, params)
        # update epoch dict
        epoch_dict = {'epoch_number': epoch_number}
        epoch_dict.update(result)
        model["epochs"].append(Epoch(epoch_dict))
        if epoch_number != len(model["epochs"]) - 1:
            print('Warning: adding epoch %d but found only %d epochs in model'
                  % (epoch_number, len(model['epochs'])))
        # add model to architecture
        # this works only because model hasn't been saved yet
        if model not in arch["fitted_models"]:
            arch["fitted_models"].append(model)
        # save result
        saved_arch = arch.save(self.db)
        saved_model = model.save(self.db)
        print("Saved arch %s; epoch number %d" % (arch_name, epoch_number))
        # return unique identifiers
        arch_key = saved_arch['pk']
        model_key = saved_model['timestamp']
        return arch_key, model_key

    def _model_from_params(self, params):
        print("Adding new model to architecture")
        params.update({"epochs": []})
        return FittedModel(params)

    def getfitted(self, model_id, params):
        "get a fitted model by id, bypassing the architecture"
        self._reconnect()
        if not model_id:
            return self._model_from_params(params)
        try:
            return self.db.get(FittedModel, {'timestamp': model_id})
        except FittedModel.DoesNotExist:
            return self._model_from_params(params)

    def getarch(self, architecture_name, corpus, **kwargs):
        """
        Gets arch. Accepts extra paramters to make the query more precise.
        """
        self._reconnect()
        arch_query = {"architecture_name": architecture_name, "corpus": corpus}
        arch_query.update(kwargs)
        try:
            arch = self.db.get(Architecture, arch_query)
        except Architecture.DoesNotExist:
            arch = {}
        return arch

    def getarchs(self, **kwargs):
        """
        Get all stored archs.
        """
        self._reconnect()
        arch_query = kwargs
        return self.db.filter(Architecture, arch_query)

    def getpreferred(self, architecture_name, corpus, **kwargs):
        """
        Gets the model params set to be preferred.
        Throws blitzdb.Document.DoesNotExist.
        """
        self._reconnect()
        arch_query = {"architecture_name": architecture_name, "corpus": corpus}
        arch_query.update(kwargs)
        arch = self.db.get(Architecture, arch_query)
        try:
            return {k: v
                    for k, v in arch.preferred_params.attributes.items()
                    if k != "pk"}
        except AttributeError:
            return {}

    def setpreferred(self, architecture_name, corpus, preferred_params,
                     **kwargs):
        """
        Sets given params as preferred for a given model
        """
        self._reconnect()
        arch_query = {"architecture_name": architecture_name, "corpus": corpus}
        arch_query.update(kwargs)
        try:
            arch = self.db.get(Architecture, arch_query)
        except Architecture.DoesNotExist:
            arch = Architecture({"architecture_name": architecture_name,
                                 "corpus": corpus,
                                 "fitted_models": [],
                                 "preferred_params": {}})

        arch["preferred_params"] = PreferredParams(preferred_params)
        arch.save(self.db)
