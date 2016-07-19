#!/usr/bin/python
# -*- coding: utf-8 -*-

from blitzdb import Document
import uuid


"""
IDEA: architectures have multiple models.
models are different based on params and corpus.
models have epochs, which is performance on a certain
corpus on a certain epoch given params and a corpus.
"""


class Architecture(Document):
    class Meta(Document.Meta):
        primary_key = "arch_id"

    def autogenerate_pk(self):
        self.pk = str(uuid.uuid1())


class FittedModel(Document):
    class Meta(Document.Meta):
        primary_key = "model_id"

    def autogenerate_pk(self):
        self.pk = str(uuid.uuid1())


class Epoch(Document):
    pass


class PreferredParams(Document):
    pass
