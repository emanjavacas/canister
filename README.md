
# Casket

#### A humble researcher's library to facilitate experiment output logging
---

## Rationale
Machine Learning experiment often produce large outputs in terms of models, parameter combinations, results and serialized systems, which can quickly become overwhelming and tedious to log and track. `Casket` aims at providing some little, but effective, help with this task .

## Installation

The packages is indexed in PiPy, which means you can just do ```pip install casket```
to get the package.

> As of today, Casket is still in a pre-release state (indicated by a version number matching following regex `0.0.[0-9]+a0`). Therefore, you might have to run `pip install casket --pre` instead.

Although it is not required to use the core functions, some functionality depends on modern versions of the packages `Keras` and `paramiko`.
More concretely, `casket.DBCallback` depends on `keras.callbacks.Callback` (the former being a subclass of the latter) and access to remote db files depends on `paramiko` being installed.

## Basic use

Basic functionality is provided by the `casket.Experiment` class.

- For instance, given a text classification problem with `sklearn`...

``` python
TODO: add example
```


- For instance, given a neural network model `model`, you can store your training history
as follows:

``` python

model_params = {input_dim: 1000, hidden_dim: 500, optimizer='rmsprop'}
model = make_model(model_params)

from casket import Experiment as E

model_db = E.use('path/to/db.json', exp_id='my experiment').model('my model')
with model_db.session(model_params) as session:
    for epoch in range(epochs):
        model.fit(X_train, y_train)
        loss, acc = model.test_on_batch(X_dev, y_dev)
        session.add_epoch(epoch + 1, {loss: loss, acc: acc})
    _, test_acc = model.test_on_batch(X_test, y_test)
    session.add_result({'acc': test_acc})
```



## Roadmap

#### API

- Experiment.Model.add_batch

#### Scripts

- Clean-up scripts (clean empty models)
- CLI tools to paginate through a db's entries

#### Support different (not only JSON-based) storages

- SQlite
- BlitzDB
- Remove services (e.g. remote MongoDB instance)

#### Web-based dashboard to visualize experiment files
