
import os
import types


def lines_from_file(fname):
    with open(fname, 'r') as f:
        for line in f:
            yield line


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
        ------------
        root: str/generator, source of lines. If str, it is coerced to file/dir
        context: int, context characters around target char
        side: str, one of 'left', 'right', 'both', context origin
        """
        self.root = root
        self.context = context
        if side not in {'left', 'right', 'both'}:
            raise ValueError('Invalid side value [%s]' % side)
        self.side = side

    def _encode_line(self, line, indexer, **kwargs):
        encoded_line = [indexer.encode(c, **kwargs) for c in line]
        maxlen = len(encoded_line)
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
        """
        Returns:
        --------
        generator over characters in root
        """
        if isinstance(self.root, types.GeneratorType):
            for line in self.root:
                for char in line:
                    yield char
        elif isinstance(self.root, str):
            if os.path.isdir(self.root):
                for f in os.listdir(self.root):
                    for line in lines_from_file(os.path.join(self.root, f)):
                        for char in line:
                            yield char
            elif os.path.isfile(self.root):
                for line in lines_from_file(self.root):
                    for char in line:
                        yield char

    def generate(self, indexer, **kwargs):
        """
        Returns:
        --------
        generator (list:int, int) over instances
        """
        if isinstance(self.root, types.GeneratorType):
            for line in self.root:
                for c, l in self._encode_line(line, indexer, **kwargs):
                    yield c, l
        elif isinstance(self.root, str):
            if os.path.isdir(self.root):
                for f in os.listdir(self.root):
                    for l in lines_from_file(os.path.join(self.root, f)):
                        for c, l in self._encode_line(l, indexer, **kwargs):
                            yield c, l
            elif os.path.isfile(self.root):
                for line in lines_from_file(self.root):
                    for c, l in self._encode_line(line, indexer, **kwargs):
                        yield c, l

    def generate_batches(self, indexer, batch_size=128, **kwargs):
        """
        Returns:
        --------
        generator (list:list:int, list:int) over batches of instances
        """
        contexts, labels, n = [], [], 0
        gen = self.generate(indexer, **kwargs)
        while True:
            try:
                context, label = next(gen)
                if n % batch_size == 0 and contexts:
                    yield contexts, labels
                    contexts, labels = [], []
                else:
                    contexts.append(context)
                    labels.append(label)
                    n += 1
            except StopIteration:
                break
