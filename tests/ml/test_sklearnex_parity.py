"""Parity of scikit-learn-intelex (sklearnex) vs stock scikit-learn.

Skips when the optional ``ml-cpu`` extra is not installed
(``uv sync --extra ml-cpu``).  Each estimator is fit stock, then patched, on a
fixed-seed dataset; divergences are asserted within per-estimator tolerances.
"""

from __future__ import annotations

import importlib

import numpy as np
import pytest


sklearnex = pytest.importorskip("sklearnex")

from sklearn.datasets import make_blobs, make_classification
from sklearn.metrics import adjusted_rand_score


SEED = 7
_MODULES = {
    "KMeans": "sklearn.cluster",
    "PCA": "sklearn.decomposition",
    "LogisticRegression": "sklearn.linear_model",
    "RandomForestClassifier": "sklearn.ensemble",
    "KNeighborsClassifier": "sklearn.neighbors",
}


def _cls(name: str, patched: bool):
    """Return estimator class with sklearnex patching on/off (global toggle)."""
    from sklearnex import patch_sklearn, unpatch_sklearn

    unpatch_sklearn()
    if patched:
        patch_sklearn(name=[f"{_MODULES[name]}.{name}"], verbose=False)
    mod = importlib.import_module(_MODULES[name])
    cls = getattr(mod, name)
    if patched:
        assert "sklearnex" in cls.__module__ or "daal4py" in cls.__module__
    else:
        assert cls.__module__.startswith("sklearn.")
    return cls


@pytest.fixture(autouse=True)
def _restore_stock():
    yield
    from sklearnex import unpatch_sklearn

    unpatch_sklearn()


@pytest.fixture(scope="module")
def clf_data():
    X, y = make_classification(
        n_samples=3000, n_features=20, n_informative=10, n_classes=3, random_state=SEED
    )
    return X[:2400], y[:2400], X[2400:], y[2400:]


def test_pca_parity(clf_data):
    X = clf_data[0]
    outs = []
    for patched in (False, True):
        m = _cls("PCA", patched)(n_components=5, svd_solver="full", random_state=SEED).fit(X)
        outs.append((m.explained_variance_ratio_, np.abs(m.transform(X))))  # sign-agnostic
    np.testing.assert_allclose(outs[0][0], outs[1][0], rtol=1e-6, atol=1e-8)
    np.testing.assert_allclose(outs[0][1], outs[1][1], rtol=1e-5, atol=1e-6)


def test_logreg_parity(clf_data):
    Xtr, ytr, Xte, _ = clf_data
    res = []
    for patched in (False, True):
        m = _cls("LogisticRegression", patched)(max_iter=1000, tol=1e-8).fit(Xtr, ytr)
        res.append((m.predict(Xte), m.predict_proba(Xte)))
    assert (res[0][0] == res[1][0]).mean() >= 0.995
    np.testing.assert_allclose(res[0][1], res[1][1], atol=1e-3)


def test_knn_parity(clf_data):
    Xtr, ytr, Xte, _ = clf_data
    preds = []
    for patched in (False, True):
        m = _cls("KNeighborsClassifier", patched)(n_neighbors=7).fit(Xtr, ytr)
        preds.append((m.predict(Xte), m.predict_proba(Xte)))
    assert (preds[0][0] == preds[1][0]).mean() >= 0.995  # distance ties may flip
    np.testing.assert_allclose(preds[0][1], preds[1][1], atol=1e-6)


def test_kmeans_parity():
    X, _ = make_blobs(n_samples=4000, n_features=8, centers=5, cluster_std=1.5, random_state=SEED)
    res = []
    for patched in (False, True):
        m = _cls("KMeans", patched)(n_clusters=5, n_init=10, random_state=SEED).fit(X)
        res.append((m.inertia_, m.labels_))
    assert abs(res[0][0] - res[1][0]) / res[0][0] < 0.03
    assert adjusted_rand_score(res[0][1], res[1][1]) > 0.9


def test_random_forest_parity(clf_data):
    Xtr, ytr, Xte, yte = clf_data
    acc = []
    for patched in (False, True):
        m = _cls("RandomForestClassifier", patched)(
            n_estimators=100, random_state=SEED, n_jobs=1
        ).fit(Xtr, ytr)
        acc.append(float((m.predict(Xte) == yte).mean()))
    assert abs(acc[0] - acc[1]) <= 0.04  # exact equality NOT expected (different RNG/binning)
