
# Casket

#### A humble researcher's library to facilitate experiment output logging
---

## Rationale
Machine Learning experiment often produce large outputs in terms of models, parameter combinations, results and serialized systems, which can quickly become overwhelming and tedious to log and track. `Casket` aims at providing some little, but effective, help with this task .

## Installation

The packages is indexed in PiPy, which means you can just do `pip install casket`
to get the package.

> As of today, Casket is still in a pre-release state (indicated by a version number matching following regex `0.0.[0-9]+a0`). Therefore, you might have to run `pip install casket --pre` instead.

Although it is not required to use the core functions, some functionality depends on modern versions of the packages `Keras` and `paramiko`.
More concretely, `casket.DBCallback` depends on `keras.callbacks.Callback` (the former being a subclass of the latter) and access to remote db files depends on `paramiko` being installed.

## Basic use

Casket organizes results at the three following levels

| Instance   | Identifier                              |
|:----------:|:---------------------------------------:|
| DB         | file path                               |
| Experiment | `exp_id` or overriden Experiment.get_id |
| Model      | `model_id`                              |


#### DB

When instantiating a experiment, you have to provide a `path`, which points to the
file where you want your results to be stored (a file will be created if none exists).
You can choose to have separate files per project or you can choose a global file.
> If `paramiko` is installed, you can also point to a remote file using the following
> syntax (see casket.sftp_storage for more info):

> ``` python
> from casket import Experiment as E
> model_db = E.use('username@knownhost:~/db.json', exp_id='my experiment')
> ```

#### Experiment

Experiments are identified by the parameter `exp_id`:

``` python
from casket import Experiment as E
experiment = E.use('/path/to/db.json', exp_id='my experiment')
```

You can also overwrite `Experiment.get_id` in a subclass, in which case `exp_id` won't
be taken into account. For instance, here we use the current python file as experiment
id, therefore avoiding hardcoding the experiment id.

``` python
from casket import Experiment as E
import inspect

class MyExperiment(E):
    def get_id(self):
        return inspect.getsourcefile(self)
```

#### Model

Finally, models have a non-optional argument which is used to uniquely identify the model. Model is a child class inside Experiment, which you can/should instantiate using the
`Experiment.model` method.

``` python
from casket import Experiment as E
model_db = E.use('/path/to/db.json', exp_id='my experiment').model('model id')
```

> In many cases you want to store information more than one time during an experiment
run. For instance, in the case of neural network training you might want to store
results for each epoch. For these cases Casket provides a `session` context manager
that will take care of inserting the corresponding result to the current experiment
run. (See below Neural Network example).
  
## Examples
Basic functionality is provided by the `casket.Experiment` class.

- For instance, given a text classification problem with `sklearn`...




- For instance, given a neural network model `model`, you can store your training history
as follows:

<div class="highlight highlight-source-python">
<pre>
params = {"input_dim": 1000, "hidden_dim": 500, "optimizer": "rmsprop"}
model = make_model(model_params)

<strong>from casket import Experiment as E</strong>

<strong>model_db = E.use('path/to/db.json', exp_id='my experiment').model('my model')</strong>
<strong>with model_db.session(model_params) as session:</strong>
    for epoch in range(epochs):
        model.fit(X_train, y_train)
        loss, acc = model.test_on_batch(X_dev, y_dev)
        <strong>session.add_epoch(epoch + 1, {loss: loss, acc: acc})</strong>
    loss, test_acc = model.test_on_batch(X_test, y_test)
    <strong>session.add_result({'acc': test_acc})</strong>
</pre>
</div>


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
