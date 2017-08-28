#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import numpy as np

from keras.models import Sequential
from keras.layers.core import Activation, Dropout, Dense
from keras.layers.recurrent import GRU

from casket.callback import DBCallback


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
    parser.add_argument('-p1', '--param_1', default=4, type=int)
    parser.add_argument('-e', '--nb_epochs', default=10, type=int)
    parser.add_argument('-t', '--tags', type=str, nargs="+", default=["NN"])

    args = vars(parser.parse_args())

    params = {                  # experiment_params
        "item_length": args['param_1'],
        "iters": 10,
        "batch_size": 10,
        "nb_epoch": args['nb_epochs'],
        "validation_split": 0.2
    }

    db_callback = DBCallback(args['name'],
                             corpus="generated",
                             tags=args["tags"],
                             params=params)

    print("Loading data.")
    data = create_data(params["item_length"], params["iters"])
    (X_train, y_train), (X_test, y_test) = train_test_split(data)

    print("Compiling model.")
    model = Sequential()
    model.add(GRU(10,
                  input_dim=1,
                  return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(1))
    model.add(Activation("linear"))
    model.compile(loss="mean_squared_error", optimizer="rmsprop")

    print("Starting learning.")
    model.fit(X_train, y_train,
              batch_size=params["batch_size"],
              nb_epoch=params["nb_epoch"],
              validation_split=params["validation_split"],
              callbacks=[db_callback])
