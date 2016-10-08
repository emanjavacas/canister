# coding: utf-8

import os
import json
from getpass import getpass

from paramiko import SSHClient, AutoAddPolicy
from tinydb import Storage


class WrongPathException(Exception):
    pass


def parse_url(url):
    """
    Extracts username, host and filename from a scp like url.
    >>> parse_url('johndoe@localhost:~/filename.txt')
    ('johndoe', 'localhost', '~/filename.txt')
    """
    if '@' not in url:
        raise WrongPathException("Bad url format: missing host")
    username, url = url.split("@")
    if not username:
        raise WrongPathException("Couldn't parse url: missing username")
    host, filename = url.split(':')
    return username, host, filename


def find_home(ssh):
    stdin, stdout, stderr = ssh.exec_command("echo $HOME")
    return stdout.readlines()[0].strip()


class SFTPStorage(Storage):
    def __init__(self, path, password=None, policy='default', **kwargs):
        self.username, self.host, self.path = parse_url(path)
        self.kwargs = kwargs
        ssh = SSHClient()
        ssh.load_system_host_keys()
        if policy == 'autoadd':
            ssh.set_missing_host_key_policy(AutoAddPolicy())
        password = password or getpass(
            'Password for %s@%s: ' % (self.username, self.host))
        ssh.connect(self.host, username=self.username, password=password)
        self.ssh = ssh
        self.sftp = ssh.open_sftp()
        if self.path.startswith('~'):
            self.path = os.path.join(find_home(self.ssh), self.path[2:])
        self.sftp.open(self.path, mode='a').close()
        self._handle = self.sftp.open(self.path, mode='r+')

    def read(self):
        self._handle.seek(0, 2)
        size = self._handle.tell()
        if not size:
            return None
        else:
            self._handle.seek(0)
            return json.loads(self._handle.read().decode('utf-8'))

    def write(self, data):
        self._handle.seek(0)
        serialized = json.dumps(data, **self.kwargs)
        self._handle.write(serialized)
        self._handle.flush()
        self._handle.truncate(self._handle.tell())

    def close(self):
        self._handle.close()
        self.ssh.close()
        self.sftp.close()

