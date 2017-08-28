
import logging
import json

try:
    import cPickle as p
except ImportError:
    import pickle as p

LOGGER = logging.getLogger(__name__)


class Indexer(object):
    def __init__(self, pad='~', oov='±', verbose=False):
        """
        Parameters:
        -----------
        reserved: dict {int: any}, preindexed reserved items.
        This is useful in case of reserved values (e.g. padding).
        Indices must start at 0.

        Example:
        --------
        indexer = Indexer()
        """
        self.level = logging.WARN if verbose else logging.NOTSET
        self.pad = pad
        self.oov = oov
        self.decoder = {}
        self.encoder = {}
        self._current = 0
        if pad:
            self.pad = pad
            self.pad_code = self.encode(pad, fitted=False)
        if oov:
            self.oov = oov
            self.oov_code = self.encode(oov, fitted=False)

    def vocab(self):
        return self.encoder.keys()

    def vocab_len(self):
        return len(self.encoder)

    def set_verbose(self, verbose=True):
        self.level = logging.WARN if verbose else logging.NOTSET

    def fit(self, seq):
        self.fitted = True
        return self.encode_seq(seq, fitted=False)

    def transform(self, seq):
        if not self.fitted:
            raise ValueError("Indexer hasn't been fitted yet")
        return self.encode_seq(seq, fitted=True)

    def fit_transform(self, seq):
        return self.fit(seq)

    def encode(self, s, fitted=True):
        """
        Parameters:
        -----------
        s: object, object to index

        Returns:
        --------
        idx (int)
        """
        if s in self.encoder:
            return self.encoder[s]
        elif fitted:
            if self.oov:
                return self.oov_code
            else:
                raise KeyError("Unknown value [%s] with no OOV default" % s)
        else:
            LOGGER.log(self.level, "Inserting new item [%s]" % s)
            idx = self._current
            self.encoder[s] = idx
            self.decoder[idx] = s
            self._current += 1
            return idx

    def decode(self, idx):
        return self.decoder[idx]

    def encode_seq(self, seq, **kwargs):
        return [self.encode(x, **kwargs) for x in seq]

    def _to_json(self):
        obj = {'encoder': self.encoder, 'decoder': self.decoder}
        if self.pad:
            obj.update({'pad': self.pad, 'pad_code': self.pad_code})
        if self.oov:
            obj.update({'oov': self.oov, 'oov_code': self.oov_code})
        return obj

    def save(self, fname, mode='json'):
        if mode == 'json':
            with open(fname, 'w') as f:
                json.dump(self._to_json(), f)
        elif mode == 'pickle':
            with open(fname, 'wb') as f:
                p.dump(self, f)
        else:
            raise ValueError('Unrecognized mode %s' % mode)

    @staticmethod
    def load(fname, mode='json'):
        if mode == 'pickle':
            with open(fname, 'rb') as f:
                return p.load(f)
        elif mode == 'json':
            with open(fname, 'r') as f:
                return Indexer.from_dict(json.load(f))
        else:
            raise ValueError('Unrecognized mode %s' % mode)

    @classmethod
    def from_dict(cls, d, **kwargs):
        idxr = cls(**kwargs)
        idxr.encoder = d['encoder']
        idxr.decoder = {int(k): v for (k, v) in d['decoder'].items()}
        idxr.fitted = True
        idxr._current = len(idxr.encoder)
        if 'pad' in d:
            idxr.pad = d['pad']
            idxr.pad_code = idxr.encode(idxr.pad, fitted=True)
        if 'oov' in d:
            idxr.oov = d['oov']
            idxr.oov_code = idxr.encode(idxr.oov, fitted=True)
        return idxr
