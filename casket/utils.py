
import inspect
import os
from datetime import datetime
from contextlib import contextmanager
import sys


@contextmanager
def silence(stderr=True, stdout=True):
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        old_stdout = sys.stdout
        sys.stderr = devnull
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr
            sys.stdout = old_stdout


def get_dir(fname):
    if os.path.isfile(fname):
        return os.path.dirname(fname)
    elif os.path.isdir(fname):
        return fname
    else:
        raise ValueError("Not valid path %s" % fname)


def getsourcefile(f):
    """
    Returns the file in which function `f` was defined.
    """
    return os.path.realpath(inspect.getsourcefile(f))


def parse_date(string_date):
    """
    >>> now = datetime.now()
    >>> assert now == parse_date(str(now))
    """
    return datetime.strptime(string_date, "%Y-%m-%d %H:%M:%S.%f")


def make_hash(o):
    """
    Returns a hash number for an object, which can also be a dict or a list

    >>> make_hash(range(10))
    -6299899980521991026
    >>> make_hash(list(range(10)))
    -4181190870548101704
    >>> a = make_hash({'a': 1, 'b': 2, 'c': 3})
    >>> b = make_hash({'c': 3, 'a': 1, 'b': 2})
    >>> assert a == b
    """
    def freeze(o):
        if isinstance(o, dict):
            return frozenset({k: freeze(v) for k, v in o.items()}.items())
        if isinstance(o, list):
            return tuple([freeze(v) for v in o])
        return o
    return hash(freeze(o))


def merge(d1, d2):
    """
    Merges two dictionaries, nested values are overwitten by d1

    >>> d = merge({'a': 1}, {'b': 2})
    >>> assert d == {'a': 1, 'b': 2}
    >>> d = merge({'a': {'b': 2}}, {'b': 2, 'a': {'c': 3}})
    >>> assert d == {'a': {'c': 3}, 'b': 2}
    """
    return dict(d1, **d2)


def update_in(d, path, f, *args):
    """
    Parameters:
    -----------
    d: dict
    path: list of key or function
    f: update function (takes nested element or None if element isn't found)

    Applies func `f` on dict `d` on element nested specified by list `path`.
    Items in path are dictionary keys or functions. If a key doesn't match any
    element, an empty dictionary is created at that point. If a nested element
    is a list, the corresponding path item should be a pred func that takes a
    list and returns True at a desired item. If no element in list is matched,
    nothing else happens. If a pred match multiple elements, last one is used.

    # Normal nested update
    >>> d = {'c': {'d': 2}}
    >>> update_in(d, ['c', 'd'], lambda x: x + 3)
    >>> assert d == {'c': {'d': 5}}

    # Update on missing element
    >>> d = {'a': {'b': 1}}
    >>> update_in(d, ['c', 'd'], lambda x: x or [] + [3])
    >>> assert d == {'a': {'b': 1}, 'c': {'d': [3]}}

    # Update on dictionary inside nested list
    >>> d = {'a': [{'b': {'c': 1}}, {'d': 2}]}
    >>> update_in(d, ['a', lambda x: 'b' in x, 'b', 'c'], lambda x: x + 3)
    >>> assert d == {'a': [{'b': {'c': 4}}, {'d': 2}]}

    # Non update on failing pred
    >>> d = {'a': [{'b': {'c': 1}}, {'d': 2}]}
    >>> update_in(d, ['a', lambda x: 'e' in x, 'b', 'c'], lambda x: x + 3)
    >>> assert d == {'a': [{'b': {'c': 1}}, {'d': 2}]}

    # Update on first matching element of list
    >>> d = {'a': [{'b': {'c': 1}}, {'d': 2}, {'b': {'c': 2}}]}
    >>> update_in(d, ['a', lambda x: 'b' in x, 'b', 'c'], lambda x: x + 3)
    >>> assert d == {'a': [{'b': {'c': 1}}, {'d': 2}, {'b': {'c': 5}}]}
    """
    if len(path) == 1:
        if callable(path[0]):
            assert isinstance(d, list), "Found pred but target is %s" % type(d)
            for idx, i in list(enumerate(d))[::-1]:  # reverse list
                if path[0](i):
                    d[idx] = f(i, *args)
                    return
        else:
            d[path[0]] = f(d.get(path[0]), *args)
    else:
        if callable(path[0]):
            assert isinstance(d, list), "Found pred but target is %s" % type(d)
            for i in d[::-1]:
                if path[0](i):
                    update_in(i, path[1:], f, *args)
                    break       # avoid mutating multiple instances
        else:
            if path[0] not in d:
                d[path[0]] = {}
            update_in(d[path[0]], path[1:], f, *args)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
