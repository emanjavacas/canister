import codecs
import json
import os

from werkzeug.routing import BaseConverter


def flatten(iterable):
    for i in iterable:
        if hasattr(i, '__iter__'):
            for j in flatten(i):
                yield j
        else:
            yield i


def get_config(in_fn='config.json'):
    root_path = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(root_path, in_fn)
    with codecs.open(file_path, 'r', 'utf-8') as f:
        config = json.load(f)
        config['secret_key'] = os.urandom(24)
        return config


class SSE(object):
    def __init__(self, data, event='message', **kwargs):
        event_map = {
            'data': data,
            'event': event
        }
        event_map.update(kwargs)
        self.event_map = event_map

    def encode(self):
        buffer = ''
        for k in ['retry', 'id', 'event', 'data']:
            if k in self.event_map:
                buffer += '%s: %s\n' % (k, self.event_map[k])
        return buffer + '\n'


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


CONFIG = get_config()
