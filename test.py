
from keras.models import Sequential
from keras.layers.core import Activation, Dropout, Dense
from keras.layers.recurrent import GRU

import numpy as np

from callback import DBCallback


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


def create_data(item_length, n_items):
    data = np.arange(item_length).reshape((item_length, 1))
    for i in xrange(n_items):
        data = np.append(data, data, axis=0)
    return data

if __name__ == '__main__':

    params = {                  # experiment_params
        "item_length": 4,
        "n_items": 10,
        "batch_size": 7,
        "nb_epoch": 10,
        "validation_split": 0.1
    }

    arch_params = {             # model architecture params
        "in_out_neurons": 1,
        "hidden_neurons": 10
    }

    db_callback = DBCallback("my Project", params=params)

    print("Loading data.")
    data = create_data(params["item_length"], params["n_items"])
    (X_train, y_train), (X_test, y_test) = train_test_split(data)

    print("Compiling model.")
    model = Sequential()
    model.add(GRU(arch_params["hidden_neurons"],
                  input_dim=arch_params["in_out_neurons"],
                  return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(arch_params["in_out_neurons"]))
    model.add(Activation("linear"))
    model.compile(loss="mean_squared_error", optimizer="rmsprop")

    print("Starting learning.")
    model.fit(X_train, y_train,
              batch_size=params["batch_size"],
              nb_epoch=params["nb_epoch"],
              validation_split=params["validation_split"],
              callbacks=[db_callback])

    # predicted = model.predict(X_test)
    # print np.sqrt(((predicted - y_test) ** 2).mean(axis=0)).mean()
    # print predicted


# from blitzdb import FileBackend
# from storage import Model
# keras_be = FileBackend("db-data")
# model = list(keras_be.filter(Model, {}))
