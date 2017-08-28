#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import numpy as np
from inspect import getsourcefile
from time import time

from keras.models import Model
from keras.layers import Input, Dense
from keras.layers.recurrent import GRU

from casket.experiment import Experiment


def load_data(data, steps=4):
    X, Y = [], []
    for i in range(0, data.shape[0]-steps):
        X.append(data[i: i+steps, :])
        Y.append(data[i+steps, :])
    return np.array(X), np.array(Y)


def train_test_split(data, test_size=0.15):
    X, Y = load_data(data)
    ntrn = round(X.shape[0] * (1 - test_size))
    X_train, Y_train = X[0:ntrn], Y[0:ntrn]
    X_test, Y_test = X[ntrn:], Y[ntrn:]
    return (X_train, Y_train), (X_test, Y_test)


def create_data(item_length, iters):
    data = np.arange(item_length).reshape((item_length, 1))
    for i in range(iters):
        data = np.append(data, data, axis=0)
    return data

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('-l', '--item_length', default=4, type=int)
    parser.add_argument('-e', '--nb_epochs', default=10, type=int)

    args = vars(parser.parse_args())

    params = {                  # experiment_params
        "item_length": args['item_length'],
        "iters": 10,
        "batch_size": 10,
        "nb_epoch": args['nb_epochs'],
        "validation_split": 0.2
    }

    print("Loading data.")
    data = create_data(params["item_length"], params["iters"])
    (X_train, y_train), (X_test, y_test) = train_test_split(data)

    print("Compiling model.")
    in_layer = Input(shape=(4, 1,))
    gru = GRU(10, dropout_W=0.2, dropout_U=0.2)(in_layer)
    dense = Dense(1, activation='linear')(gru)
    model = Model(input=in_layer, output=dense)
    model.compile(loss="mean_squared_error", optimizer="rmsprop", metrics=['accuracy'])

    exp_id = getsourcefile(lambda: 0)
    model_db = Experiment.use("test.json", exp_id=exp_id) \
                         .model("test-model", model.get_config())
    start = time()

    print("Starting learning.")
    with model_db.session(params, ensure_unique=False) as session:
        for e in range(params["nb_epoch"]):
            losses, batch = [], 0
            while batch < X_train.shape[0]:
                batch_to = max(batch + params["batch_size"], X_train.shape[0])
                X_batch, y_batch = X_train[batch: batch_to], y_train[batch: batch_to]
                batch = batch_to
                loss = model.train_on_batch(X_train, y_train)
                losses.append(loss)
                print(np.mean(losses))
            session.add_epoch(e, {'loss': str(np.mean(losses))})
        _, acc = model.test_on_batch(X_test, y_test)
        session.add_result({'test_acc': str(acc)})
        session.add_meta({'run_time': time() - start})
