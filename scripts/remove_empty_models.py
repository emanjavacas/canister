#!/usr/bin/env python

import argparse


def remove_where(field, match_fn):
    def transform(element):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Remove empty models from a db')
    parser.add_argument('db-path')
    args = parser.parse_args()

