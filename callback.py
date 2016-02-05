#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function

from keras.callbacks import Callback
from modelbase import ModelBase


class DBCallback(Callback):
    """
    Stores and updates a model experiment. A model_id should be used
    for each new model architecture, this enforces that experiments
    based on the same architecture are stored together.
    Parameters
    ----------

    params: dict
        A dictionary of parameters used in the current experiment.

    db_path: str, optional, default 'db-data'
        Path to the store dir to be used by blitzdb.FileBackend.

    freq: int, optional, default 1
        Number of epochs before commiting results to database.
        Can be use to skip over epochs.

    Attributes
    ----------
    backend: blitzdb.FileBackend
        File backend.

    experiment: blitzdb.Document
        Document representing the experiment as stored in the database.

    doc: blitzdb.Document
        Document representing the model as stored in the database.

        """

    def __init__(self, arch_name, corpus, path='db-data', freq=1):
        "sets the database connection"
        self.arch_name = arch_name
        self.corpus = corpus
        self.mb = ModelBase(path)
        self.freq = freq
        super(Callback, self).__init__()

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
            self.md.addresult(architecture_name=self.arch_name, corpus=self.corpus)
            self.experiment.attributes["epochs"][epoch] = epoch_data
            self.experiment.save(self.backend)

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
        self.params "merge" = self.model.get_config()

    def on_train_end(self, logs={}):
        self.experiment.attributes.update({"status": "finished"})
        self.experiment.save(self.backend)
