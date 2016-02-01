import codecs
import json
import os


def get_config(in_fn='config.json'):
    root_path = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(root_path, in_fn)
    with codecs.open(file_path, 'r', 'utf-8') as f:
        config = json.load(f)
        return config


CONFIG = get_config()
