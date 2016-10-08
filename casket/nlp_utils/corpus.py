
import os
import types


def lines_from_file(fname):
    with open(fname, 'r') as f:
        for line in f:
            yield line


def lines_from_root(root):
    if isinstance(root, types.GeneratorType):
        for line in root:
            yield line
    elif isinstance(root, str):
        if os.path.isdir(root):
            for f in os.listdir(root):
                for l in lines_from_file(os.path.join(root, f)):
                    yield l
    elif os.path.isfile(root):
        for line in lines_from_file(root):
            yield line
    else:
        raise ValueError("Unknown root type [%s]" % type(root))


def pad(items, maxlen, paditem=0, paddir='left'):
    """
    Parameters:
    -----------
    items: iterable, an iterable of objects to index
    maxlen: int, length to which input will be padded
    paditem: any, element to use for padding
    paddir: ('left', 'right'), where to add the padding
    """
    n_items = len(items)
    if n_items == maxlen:
        return items
    if paddir == 'left':
        return (maxlen - n_items) * [paditem] + items
    if paddir == 'right':
        return items + (maxlen - n_items) * [paditem]
    else:
        raise ValueError("Unknown pad direction [%s]" % str(paddir))


class Corpus(object):
    def __init__(self, root, context=10, side='both'):
        """
        Parameters:
        -----------
        root: str/generator, source of lines. If str, it is coerced to file/dir
        context: int, context characters around target char
        side: str, one of 'left', 'right', 'both', context origin
        """
        self.root = root
        self.context = context
        if side not in {'left', 'right', 'both'}:
            raise ValueError('Invalid side value [%s]' % side)
        self.side = side

    def _pad_encode(self, line, indexer, **kwargs):
        """
        Parameters:
        -----------
        line: generator/list, a seq of units to be padded/encoded
        indexer: Indexer, a fitted indexer
        kwargs: optional arguments for Indexer.encode

        Returns:
        --------
        generator over (context, target)
        """
        maxlen = len(line)
        encoded_line = [indexer.encode(c, **kwargs) for c in line]
        for idx, c in enumerate(encoded_line):
            minidx = max(0, idx - self.context)
            maxidx = min(maxlen, idx + self.context + 1)
            if self.side in {'left', 'both'}:
                left = pad(encoded_line[minidx: idx], self.context,
                           paditem=indexer.pad_code, paddir='left')
            if self.side in {'right', 'both'}:
                right = pad(encoded_line[idx + 1: maxidx], self.context,
                            paditem=indexer.pad_code, paddir='right')
            if self.side == 'left':
                yield left, c
            elif self.side == 'right':
                yield right, c
            else:
                yield left + right, c

    def chars(self):
        for line in lines_from_root(self.root):
            for c in line:
                yield c

    def words(self, tokenizer=None):
        for line in lines_from_root(self.root):
            if tokenizer is not None:
                for word in tokenizer(line):
                    yield word
            else:
                for word in line.split():
                    yield word

    def generate(self, mode='chars', tokenizer=None, indexer=None, **kwargs):
        """
        Returns:
        --------
        generator (list:int, int) over instances
        """
        for line in lines_from_root(self.root):
            if mode == 'chars':
                for c, t in self._pad_encode(line, indexer, **kwargs):
                    yield c, t
            elif mode == 'words':
                words = tokenizer(line) if tokenizer else line.split()
                for word, t in self._pad_encode(words, indexer, **kwargs):
                    yield word, t
            else:
                raise ValueError("Unknown mode [%s]" % str(mode))

    def generate_batches(self, batch_size=128, **kwargs):
        """
        Parameters:
        -----------
        batch_size: int
        kwargs: optional arguments for Corpus.generate and Indexer.encode

        Returns:
        --------
        generator (list:list:int, list:int) over batches of instances
        """
        contexts, targets, n = [], [], 0
        generator = self.generate(**kwargs)
        while True:
            try:
                context, target = next(generator)
                if n % batch_size == 0 and contexts:
                    yield contexts, targets
                    contexts, targets = [], []
                else:
                    contexts.append(context)
                    targets.append(target)
                    n += 1
            except StopIteration:
                break
