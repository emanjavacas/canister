#!/usr/bin/python
# -*- coding: utf-8 -*-

from blitzdb import Document
from time import time

"""
IDEA: architectures have multiple models.
models are different based on params and corpus.
models have epochs, which is performance on a certain
corpus on a certain epoch given params and a corpus.
"""


class Architecture(Document):
    pass


class FittedModel(Document):
    class Meta(Document.Meta):
        primary_key = "timestamp"

    def autogenerate_pk(self):
        self.pk = str(time())


class Epoch(Document):
    pass


class PreferredParams(Document):
    pass
