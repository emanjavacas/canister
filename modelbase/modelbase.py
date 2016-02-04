#!/usr/bin/python
# -*- coding: utf-8 -*-

import blitzdb
from blitzdocuments import Model, Architecture, Epoch, PreferredParams


class ModelBase(object):

    def __init__(self, path, local=True):

        if local:
            self.db = blitzdb.FileBackend(path, config={"autocommit": True})
        else:
            raise NotImplementedError("Mongo not supported yet")

    def addresult(self, architecture, corpus, params, features, epochnumber, result):

        try:
            arch = self.db.get(Architecture, {"type": architecture,
                                              "corpus": corpus,
                                              "features": features})
        except Architecture.DoesNotExist:
            arch = Architecture({"type": architecture,
                                 "corpus": corpus,
                                 "features": features,
                                 "models": [],
                                 "preferredparams": {}})

        try:
            model = self.db.get(Model, params)
        except Model.DoesNotExist:
            params.update({"epochs": []})
            model = Model(params)

        epochdict = {'epochnumber': epochnumber}
        epochdict.update(result)

        epoch = Epoch(epochdict)

        model["epochs"].append(epoch)
        if model not in arch.models:
            arch["models"].append(model)

        arch.save(self.db)

    def getpreferred(self, architecture, corpus, features):

        arch = self.db.get(Architecture, {"type": architecture, "features": features, "corpus": corpus})
        try:
            return {k: v for k, v in arch.preferredparams.attributes.items() if k != "pk"}
        except AttributeError:
            return {}

    def setpreferred(self, architecture, corpus, features, preferredparams):

        try:
            arch = self.db.get(Architecture, {"type": architecture,
                                              "corpus": corpus,
                                              "features": features})
        except Architecture.DoesNotExist:
            arch = Architecture({"type": architecture,
                                 "corpus": corpus,
                                 "features": features,
                                 "models": [],
                                 "preferredparams": {}})

        arch["preferredparams"] = PreferredParams(preferredparams)
        arch.save(self.db)
