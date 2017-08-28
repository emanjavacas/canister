
from tinydb import TinyDB
from itertools import chain


class DB:
    def __init__(self, path):
        try:
            from sftp_storage import SFTPStorage, WrongPathException
            try:
                self.db = TinyDB(path, policy='autoadd', storage=SFTPStorage)
            except WrongPathException:
                self.db = TinyDB(path)
        except ImportError:
            from warnings import warn
            warn("""`paramiko` doesn't seem to be installed in your OS.
            Remote db access is disabled""", ImportWarning)
            self.db = TinyDB(path)

    def get_experiments(self):
        return self.db.search()

    def get_experiment(self, experiment_id):
        return self.db.get({"id": experiment_id})

    def get_model(self, experiment_id, model_id):
        models = self.get_experiment(experiment_id)["models"]
        for m in models:
            if m["modelId"] == model_id:
                return m

    def get_tags(self):
        return chain(*[exp['tags'] for exp in self.db.search()])

    def get_timestamps(self):
        return [model["meta"]["timestamp"]
                for exp in self.get_experiments()
                for model in exp.get("models", [])]

    def get_last_timestamp(self):
        return max(self.get_timestamps)
