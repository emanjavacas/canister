
# Casket

#### A humble researcher's library to facilitate experiment output logging
---

## Rationale
Machine Learning experiment often produce large outputs in terms of models, parameter combinations, results and serialized systems, which can quickly become overwhelming and tedious to log and track. `Casket` aims at providing some little, but effective, help with this task .

## Installation

The packages is indexed in PyPI, which means you can just do `pip install casket`
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

You can also pass model parameters that will remain unchanged throughout your experiment
as an optional argument to `model(model_id, model_config=your_config_dict)`

``` python
from casket import Experiment as E
model_db = E.use('/path/to/db.json', exp_id='my experiment') \
            .model('model id', {'fixed_param1': 1, 'fixed_param2': 2})
```

> In many cases you want to store information more than one time during an experiment
run. For instance, in the case of neural network training you might want to store
results for each epoch. For these cases Casket provides a `session` context manager
that will take care of inserting the corresponding result to the current experiment
run. (See below GridSearch and Neural Network example).

> In such cases, casket with throw an `casket.ExistingParamsException` if the same
model has already been run with the same parameters. This behaviour can be changed
with the optional argument `ensure_unique` in the `session` method:
``` python
from casket import Experiment as E
model_db = E.use('/path/to/db.json', exp_id='my experiment').model('model id')
with model_db.session(session_params, ensure_unique=False)
```
> In that case results will be appended to the last model session run with
those same parameters.
  
## Examples
Basic functionality is provided by the `casket.Experiment` class.

- Simple SVM setup with `sklearn`

```
from sklearn.svm import SVC
from sklearn.metrics import accuracy
clf = SVC()
clf.fit(X_train, y_train)

from casket import Experiment as E
# instantiate model db
model = E.use('path/to/db.json', exp_id='random classification') \
         .model('SVM', model_config=clf.get_params())

y_true, y_pred = y_test, clf.predict(X_test)
# insert results
model.add_result({'accuracy': accuracy(y_true, y_pred),
                  'y_true': y_true.tolist()}) # ensure JSON serializable
```

- Grid search classification problem with `sklearn`

```
grid_params = [
    {'kernel': ['rbf'], 'gamma': [1e-3, 1e-4], 'C': [1, 10, 100, 1000]},
    {'kernel': ['linear'], 'C': [1, 10, 100, 1000]}
]

scores = ['precision', 'recall']

model = E.use('test.db', exp_id='test-run').model('digits')
with model.session({'grid_params': grid_params}) as session:
    for score in scores:
        clf = GridSearchCV(SVC(), grid_params, cv=5, scoring='%s_macro' % score)
        clf.fit(X_train, y_train)

        # add best params in dev set
        session.add_result({'best_params': clf.best_params_},
                           index_by=score) # index session results by target score

        means = clf.cv_results_['mean_test_score']
        stds = clf.cv_results_['std_test_score']
        for mean, std, params in zip(means, stds, clf.cv_results_['params']):
        
            # add partial grid search result alongside params
            result = {'grid_search_params': params,
                      'dev_scores': {'mean': mean, 'std': std}}
            session.add_result(result, index_by=score)

        y_true, y_pred = y_test, clf.predict(X_test)
        p, r, f, _ = precision_recall_fscore_support(y_true, y_pred)
        
        # add result on test set
        result = {'test_scores': {'precision': p.tolist(), # np arrays are not JSON
                                  'recall': r.tolist(),
                                  'f': f.tolist()},
                  'y_pred': y_pred.tolist()}
        session.add_result(result, index_by=score)        
```

- Neural network example

```
params = {"input_dim": 1000, "hidden_dim": 500, "optimizer": "rmsprop"}
model = make_model(model_params)

from casket import Experiment as E
# instantiate model db
model_db = E.use('path/to/db.json', exp_id='my experiment').model('my model')
with model_db.session(model_params) as session:
    for epoch in range(epochs):
        model.fit(X_train, y_train)
        loss, acc = model.test_on_batch(X_dev, y_dev)
        # use utility method `add_epoch(epoch_num, epoch_result)` to insert epoch result
        session.add_epoch(epoch + 1, {loss: loss, acc: acc})
    loss, test_acc = model.test_on_batch(X_test, y_test)
    # insert accuracy on test data
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
