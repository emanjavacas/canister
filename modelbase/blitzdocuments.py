#!/usr/bin/python
# -*- coding: utf-8 -*-

from blitzdb import Document


"""
IDEA: architectures have multiple models.
models are different based on params and corpus.
models have epochs, which is performance on a certain
corpus on a certain epoch given params and a corpus.
"""


class Architecture(Document):

    pass


class FittedModel(Document):

    pass


class Epoch(Document):

    pass


class PreferredParams(Document):

    pass
