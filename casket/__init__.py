_version = "0.0.1a"

from .experiment import Experiment
try:
    from .callback import DBCallback
    raise ImportError
except ImportError:
    from warnings import warn
    warn("Keras doesn't seem to be installed in your OS", ImportWarning)

from .nlp_utils.corpus import *
from .nlp_utils.indexer import *
