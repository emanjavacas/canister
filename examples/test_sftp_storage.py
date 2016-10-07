# coding: utf-8

import pytest

from sftp_storage import SFTPStorage
from tinydb import TinyDB, where


element = {'none': [None, None], 'int': 42, 'float': 3.1415899999999999,
           'list': ['LITE', 'RES_ACID', 'SUS_DEXT'],
           'dict': {'hp': 13, 'sp': 5},
           'bool': [True, False, True, False]}

path = 'manjavacas@serv1:~/test.json'


def test_json():
    # Write contents
    storage = SFTPStorage(path, policy='autoadd')
    storage.write(element)

    # Verify contents
    assert element == storage.read()


def test_json_readwrite():
    """
    Regression test for issue #1
    """
    # Create TinyDB instance
    db = TinyDB(path, policy='autoadd', storage=SFTPStorage)

    item = {'name': 'A very long entry'}
    item2 = {'name': 'A short one'}

    get = lambda s: db.get(where('name') == s)

    db.insert(item)
    assert get('A very long entry') == item

    db.remove(where('name') == 'A very long entry')
    assert get('A very long entry') is None

    db.insert(item2)
    assert get('A short one') == item2

    db.remove(where('name') == 'A short one')
    assert get('A short one') is None


def test_json_invalid_directory():
    with pytest.raises(ValueError):
        with TinyDB('/this/is/an/invalid/path/db.json',
                    policy='autoadd', storage=SFTPStorage):
            pass

