
import numpy as np
import inspect
from time import time

from scipy import random
from sklearn import svm
from sklearn.cross_validation import train_test_split
from sklearn.metrics import accuracy_score

from casket.experiment import Experiment


def generate_clusters(n_points=100, n_clusters=5, n_dim=3, noise=0.15):
    X = np.zeros((n_points * n_clusters, n_dim))
    y = np.zeros(n_points * n_clusters)
    for cluster in range(n_clusters):
        mean = (np.ones(n_dim) * (cluster + 1)) + (random.rand(n_dim))
        random_mat = random.rand(n_dim, n_dim)
        cov = np.dot(random_mat, random_mat.transpose())  # pos semi-definite
        sample = np.random.multivariate_normal(mean, cov, n_points)
        sample += (noise * np.random.random_sample((n_points, n_dim)))
        X[cluster * n_points: (cluster + 1) * n_points] = sample
        y[cluster * n_points: (cluster + 1) * n_points] = cluster
    return X, y


class Clustering(Experiment):
    def get_id(self):
        return inspect.getsourcefile(lambda: 0)

if __name__ == '__main__':
    X, y = generate_clusters(noise=0.5, n_clusters=4)
    X_train, X_test, y_train, y_test = \
        train_test_split(X, y, test_size=0.33, random_state=42)
    clf = svm.LinearSVC()

    model_meta = {}
    model = Clustering.use("test.db", tags=('random', 'test')) \
                      .model("LinearSVC", model_meta=model_meta)
    with model.session(clf.get_params(), ensure_unique=False) as session:
        start = time()
        clf.fit(X_train, y_train)
        end = time()
        session.add_meta({"duration": end - start})

        y_pred = clf.predict(X_test)
        session.add_result({"y_pred": y_pred.tolist(),
                            "y_test": y_test.tolist(),
                            "accuracy": accuracy_score(y_test, y_pred)})
