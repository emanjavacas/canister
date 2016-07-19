#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

from blitzdb import FileBackend
from canister.blitzdocuments import FittedModel, Architecture
from canister.blitzdocuments import Epoch, PreferredParams


logger = logging.getLogger(__name__)


def log(msg):
    logger.log(logging.INFO, msg)


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

    def add_result(self, arch_id, corpus, params, result, model_id=None,
                   epoch_number=0, arch_params={}, tags=('unknown',)):
        """
        Adds a fitted model plus associated results to a given architecture
        Parameters
        ----------
        arch_id: str/int/float,
            unique architecture identifier

        corpus: str
            Corpus used in the experiments

        params: dict (JSON-serializable)
            Experiment params

        result: dict (JSON-serializable)
            Output of the experiment

        model_id: str/int/float, optional, default `None`
            Unique model identifier to add result to.
            If `None` a new model is created with random uuid as model_id.

        epoch_number: int, optional, default 0
            Self-explaining

        arch_params: dict (JSON-serializable), optional, default {}
            Fixed architecture parameters to will be used across a experiments

        tags: tuple, optional, default ('unknown',)
        """
        self._reconnect()
        try:
            arch = self.db.get(Architecture,
                               {"arch_id": arch_id, "corpus": corpus})
        except Architecture.DoesNotExist:
            log("Creating new architecture %s" % arch_id)
            arch = Architecture({"arch_id": arch_id,
                                 "arch_params": arch_params,
                                 "corpus": corpus,
                                 "fitted_models": [],
                                 "preferred_params": {},
                                 "tags": tags})
        # fetch model
        if model_id:
            model = self.get_fitted(model_id, params)
        else:
            model = self.model_from_params(params)
        # update epoch dict
        epoch_dict = dict({'epoch_number': epoch_number}, **result)
        model["epochs"].append(Epoch(epoch_dict))
        if epoch_number != len(model["epochs"]) - 1:
            log('Warning: adding epoch %d but found only %d epochs in model'
                % (epoch_number, len(model['epochs'])))
        # add model to architecture (works since model hasn't been saved yet)
        if model not in arch["fitted_models"]:
            arch["fitted_models"].append(model)
        # save result
        arch.save(self.db)
        model.save(self.db)
        log("Saved arch %s; epoch number %d" % (str(arch_id), epoch_number))
        # return unique identifier
        return model_id

    def model_from_params(self, params):
        return FittedModel(dict(params, **{"epochs": []}))

    def get_fitted(self, model_id, params):
        "Get a fitted model by id, bypassing the architecture"
        self._reconnect()
        return self.db.get(FittedModel, {'model_id': model_id})

    def get_arch(self, arch_id, corpus, **kwargs):
        "Gets arch. Accepts extra paramters to make the query more precise"
        self._reconnect()
        arch_query = {"arch_id": arch_id, "corpus": corpus}
        arch_query.update(kwargs)
        try:
            return self.db.get(Architecture, arch_query)
        except Architecture.DoesNotExist:
            return {}

    def get_archs(self, **kwargs):
        "Get all stored archs"
        self._reconnect()
        return self.db.filter(Architecture, kwargs)

    def get_preferred(self, arch_id, corpus, **kwargs):
        """
        Gets the model params set to be preferred.
        Throws blitzdb.Document.DoesNotExist.
        """
        self._reconnect()
        arch_query = dict({"arch_id": arch_id, "corpus": corpus}, **kwargs)
        arch = self.db.get(Architecture, arch_query)
        try:
            return {k: v
                    for k, v in arch.preferred_params.attributes.items()
                    if k != "pk"}
        except AttributeError:
            return {}

    def set_preferred(self, arch_id, corpus, preferred_params, **kwargs):
        "Sets given params as preferred for a given model"
        self._reconnect()
        arch_query = dict({"arch_id": arch_id, "corpus": corpus}, **kwargs)
        try:
            arch = self.db.get(Architecture, arch_query)
        except Architecture.DoesNotExist:
            arch = Architecture({"arch_id": arch_id,
                                 "corpus": corpus,
                                 "fitted_models": [],
                                 "preferred_params": {}})
        arch["preferred_params"] = PreferredParams(preferred_params)
        arch.save(self.db)
