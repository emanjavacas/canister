#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function

import json

from keras.callbacks import Callback
from modelbase import ModelBase


class DBCallback(Callback):
    """
    Stores and updates a model experiment. A model_id should be used
    for each new model architecture, this enforces that experiments
    based on the same architecture are stored together.
    Parameters
    ----------
    arch_id: str
        architecture name

    corpus: str
        corpus used for the experiment

    params: dict
        A dictionary of parameters used in the current experiment.

    path: str, optional, default 'test.db'
        Path to the store dir to be used by blitzdb.FileBackend.

    freq: int, optional, default 1
        Number of epochs before commiting results to database.
        Can be use to skip over epochs.

    live_root: str, optional, default 'http://localhost:5000'
        URL to publish results to. Set to None if local server isn't running

    Attributes
    ----------
    mb: blitzdb.FileBackend
        File backend.

    arch_params: dict
        the result of Keras.model.get_config() to be passed to mb.addresult()

    model_id: str, int, float
        unique identifier of the stored model. Used to keep passing epochs
        to the same model (as opposed to creating a new model for each epoch)
    """

    def __init__(self, arch_id, corpus, params, tags=("NN",),
                 path='test.db', freq=1, live_root='http://localhost:5000'):
        "sets the database connection"
        self.arch_id = arch_id
        self.corpus = corpus
        self.params = params
        self.freq = freq
        self.live_root = live_root
        self.tags = tags
        self.mb = ModelBase(path)
        self.arch_params = None
        self.model_id = None
        super(Callback, self).__init__()

    def reach_server(self, data, endpoint):
        "tries to reach server at the given `endpoint` with the given `data`"
        if not self.live_root:
            return
        import requests
        try:
            requests.post(self.live_root + endpoint,
                          {'data': json.dumps(data)})
        except TypeError:
            print("JSON error; data: " + str(data))
        except:
            print("Could not reach server at " + self.live_root)

    def on_epoch_begin(self, epoch, logs={}):
        if (epoch % self.freq) == 0:
            self.seen = 0
            self.totals = {}

    def on_epoch_end(self, epoch, logs={}):
        assert self.arch_params
        if (epoch % self.freq) == 0:
            epoch_data = {}
            for k, v in self.totals.items():
                epoch_data[k] = v / self.seen
            for k, v in logs.items():  # val_...
                epoch_data[k] = v
            # send to db
            model_id = self.mb.add_result(arch_id=self.arch_id,
                                          corpus=self.corpus,
                                          params=self.params,
                                          result={"result": epoch_data},
                                          model_id=self.model_id,
                                          epoch_number=epoch,
                                          arch_params=self.arch_params,
                                          tags=self.tags)
            if not self.model_id:
                self.model_id = model_id
                self.reach_server({'action': 'start',
                                   'modelId': model_id},
                                  '/publish/train/')

            # send to localhost
            self.reach_server({'epochData': epoch_data,
                               'modelId':  model_id},
                              '/publish/epoch/end/')

    def on_batch_begin(self, batch, logs={}):
        pass

    def on_batch_end(self, batch, logs={}):
        batch_size = logs.get('size', 0)
        self.seen += batch_size
        for k, v in logs.items():  # batch, size
            if k in self.totals:
                self.totals[k] += v * batch_size
            else:
                self.totals[k] = v * batch_size

    def on_train_begin(self, logs={}):
        self.arch_params = self.model.get_config()
        pass

    def on_train_end(self, logs={}):
        self.reach_server({'modelId': self.model_id,
                           'action': 'end'},
                          '/publish/train/')
