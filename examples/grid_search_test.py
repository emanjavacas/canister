
from __future__ import print_function

from sklearn import datasets
from sklearn.model_selection import train_test_split
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import precision_recall_fscore_support
from sklearn.svm import SVC

from casket import Experiment as E

digits = datasets.load_digits()

n_samples = len(digits.images)
X = digits.images.reshape((n_samples, -1))
y = digits.target

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.5, random_state=0)

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
        session.add_result({'best_params': clf.best_params_}, index_by=score)

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
        result = {'test_scores': {'precision': p.tolist(),
                                  'recall': r.tolist(),
                                  'f': f.tolist()},
                  'y_pred': y_pred.tolist()}
        session.add_result(result, index_by=score)
