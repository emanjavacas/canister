#!/usr/bin/python
# -*- coding: utf-8 -*-

import json

from .utils import silence

with silence():
    from keras.callbacks import Callback


class DBCallback(Callback):
    """
    Stores and updates a model experiment. A model_id should be used
    for each new model architecture, this enforces that experiments
    based on the same architecture are stored together.
    Parameters
    ----------
    model: experiment.Experiment.Model

    params: dict
        A dictionary of parameters used in the current experiment run.

    freq: int, optional, default 1
        Number of epochs before commiting results to database.
        Can be use to skip over epochs.

    root: str, optional, default 'http://localhost:5000'
        URL to publish results to. Set to None if local server isn't running
    """
    def __init__(self, model, params, freq=1, root='http://localhost:5000'):
        self.model = model
        self.params = params
        self.freq = freq
        self.root = root
        super(Callback, self).__init__()

    def reach_server(self, data, endpoint):
        "tries to reach server at the given `endpoint` with the given `data`"
        if not self.root:
            return
        import requests
        try:
            requests.post(self.root + endpoint, {'data': json.dumps(data)})
        except TypeError:
            print("JSON error; data: " + str(data))
        except:
            print("Could not reach server at " + self.root)

    def on_epoch_begin(self, epoch, logs={}):
        if (epoch % self.freq) == 0:
            self.seen = 0
            self.totals = {}

    def on_epoch_end(self, epoch, logs={}):
        if (epoch % self.freq) == 0:
            epoch_data = {}
            for k, v in self.totals.items():
                epoch_data[k] = v / self.seen
            for k, v in logs.items():  # val_...
                epoch_data[k] = v
            # send to db
            self.model.add_epoch(epoch, epoch_data)

            # send to localhost
            self.reach_server(
                {'epochData': epoch_data, 'modelId': self.model.model_id},
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
        self.model._start_session(self.params)
        self.reach_server({'action': 'start', 'modelId': self.model_id},
                          '/publish/train/')

    def on_train_end(self, logs={}):
        self.model._end_session()
        self.reach_server({'action': 'end', 'modelId': self.model.model_id},
                          '/publish/train/')
