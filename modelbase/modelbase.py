#!/usr/bin/python
# -*- coding: utf-8 -*-

import blitzdb
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

        if local:
            self.db = blitzdb.FileBackend(path, config={"autocommit": True})
        else:
            raise NotImplementedError("Mongo not supported yet")

    def addresult(self, architecture_name, corpus, params, epoch_number, result,
                  architecture_params={}):
        """
        Adds a fitted model plus associated experiment results to a given architecture
        Parameters
        ----------
        architecture_name: str
            Architecture identifier

        corpus: str
            Corpus used in the experiments

        params: dict (JSON-serializable)
            Experiment params

        epoch_number: int
            Self-explaining

        result: dict (JSON-serializable)
            Output of the experiment 

        architecture_params: dict (JSON-serializable), optional, default {}
            Fixed architecture parameters that will be used across a experiments
        """
        try:
            arch = self.db.get(Architecture, {"architecture_name": architecture_name,
                                              "architecture_params": architecture_params,
                                              "corpus": corpus})
        except Architecture.DoesNotExist:
            arch = Architecture({"architecture_name": architecture_name,
                                 "architecture_params": architecture_params,
                                 "corpus": corpus,
                                 "fitted_models": [],
                                 "preferred_params": {}})

        try:
            model = self.db.get(FittedModel, params)
        except FittedModel.DoesNotExist:
            params.update({"epochs": []})
            model = FittedModel(params)

        epoch_dict = {'epoch_number': epoch_number}
        epoch_dict.update(result)

        epoch = Epoch(epoch_dict)

        model["epochs"].append(epoch)
        if model not in arch.models:
            arch["models"].append(model)

        arch.save(self.db)

    def getpreferred(self, architecture_name, corpus, features, architecture_params={}):
        """
        Gets the model params set to be preferred
        """
        arch = self.db.get(Architecture, {"architecture_name": architecture_name,
                                          "architecture_params": architecture_params,
                                          "features": features, 
                                          "corpus": corpus})
        try:
            return {k: v
                    for k, v in arch.preferred_params.attributes.items()
                    if k != "pk"}
        except AttributeError:
            return {}

    def setpreferred(self, architecture_name, corpus, features, preferred_params):
        """
        Sets given params as preferred for a given model
        """
        try:
            arch = self.db.get(Architecture, {"architecture_name": architecture_name,
                                              "architecture_params": architecture_params,
                                              "corpus": corpus,
                                              "features": features})
        except Architecture.DoesNotExist:
            arch = Architecture({"architecture_name": architecture_name,
                                 "corpus": corpus,
                                 "features": features,
                                 "models": [],
                                 "preferred_params": {}})

        arch["preferred_params"] = PreferredParams(preferred_params)
        arch.save(self.db)
