from blitzdb import Document
from time import time


class Model(Document):
    class Meta(Document.Meta):
        "Define a primary key instead of uuid"
        primary_key = 'model_id'


class Experiment(Document):
    class Meta(Document.Meta):
        primary_key = "timestamp"

    def autogenerate_pk(self):
        self.pk = str(time())
