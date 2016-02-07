
import numpy as np

from canister.modelbase import ModelBase
from scipy import random
from sklearn import svm
from sklearn.cross_validation import train_test_split
from sklearn.metrics import accuracy_score


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


if __name__ == '__main__':

    mb = ModelBase("test.db")

    X, y = generate_clusters(noise=0.5, n_clusters=4)
    X_train, X_test, y_train, y_test = \
        train_test_split(X, y, test_size=0.33, random_state=42)
    clf = svm.LinearSVC()

    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    print(accuracy_score(y_test, y_pred))

    params = clf.get_params()
    arch = svm.LinearSVC.__name__

    mb.addresult(arch_name=arch,
                 corpus="randomdata",
                 params=params,
                 epoch_number=0,
                 result={"y_pred": y_pred.tolist(), "y_test": y_test.tolist()})
