# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import gevent
import gevent.monkey
from gevent.pool import Group, Pool
import sys
import json
import os.path
import hashlib
from uuid import UUID
from pathlib import PurePosixPath, _PosixFlavour
from six import string_types, text_type, b
import collections
import logging

from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter

from prompt_toolkit.shortcuts import prompt, create_eventloop

from .exceptions import AbsPathRequired


gevent.monkey.patch_socket()
gevent.monkey.patch_ssl()
logger = logging.getLogger(__name__)
CONFIG_DIR = os.path.expanduser('~/.config/contrail-api-cli')


class FQName(collections.Sequence):

    def __init__(self, init=None):
        if isinstance(init, string_types):
            self._data = init.split(':')
        elif isinstance(init, list):
            self._data = init
        elif isinstance(init, FQName):
            self._data = init._data
        else:
            self._data = []

    def __getitem__(self, idx):
        return self._data[idx]

    def __len__(self):
        return len(self._data)

    def __eq__(self, other):
        return self._data == other

    def __repr__(self):
        return repr(self._data)

    def __str__(self):
        return ':'.join(self._data)

    def __bytes__(self):
        return b(':'.join(self._data))

    def __lt__(self, b):
        return len(text_type(self)) < len(text_type(b))

    def __gt__(self, b):
        return not self.__lt__(b)


class Observable(object):

    def __new__(cls, *args, **kwargs):
        return super(Observable, cls).__new__(cls)

    @classmethod
    def register(cls, event, callback):
        logger.debug("registering %s to %s" % (event, callback))
        if not hasattr(cls, "observers"):
            cls.observers = {}
        if event not in cls.observers:
            cls.observers[event] = []
        cls.observers[event].append(callback)

    @classmethod
    def unregister(cls, event, callback):
        try:
            cls.observers[event].remove(callback)
        except (ValueError, KeyError):
            pass

    @classmethod
    def emit(cls, event, data):
        logger.debug("emiting event %s with %s" % (event, repr(data)))
        if not hasattr(cls, "observers"):
            cls.observers = {}
        [cbk(data)
         for evt, cbks in cls.observers.items()
         for cbk in cbks
         if evt == event]


class Singleton(type):

    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(name, bases, dict)
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance


class APIFlavour(_PosixFlavour):

    def parse_parts(self, parts):
        # Handle non ascii chars for python2
        parts = [p.encode('ascii', errors='replace').decode('ascii')
                 for p in parts]
        return super(APIFlavour, self).parse_parts(parts)


class Path(PurePosixPath):
    _flavour = APIFlavour()

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts, init=True):
        if parts:
            parts = [root] + os.path.relpath(os.path.join(*parts),
                                             start=root).split(os.path.sep)
            parts = [p for p in parts if p not in (".", "")]
        return super(cls, Path)._from_parsed_parts(drv, root, parts, init)

    def __init__(self, *args):
        self.meta = {}

    @property
    def base(self):
        try:
            return self.parts[1]
        except IndexError:
            pass
        return ''

    @property
    def is_root(self):
        return len(self.parts) == 1 and self.root == "/"

    @property
    def is_fq_name(self):
        return not self.is_uuid

    @property
    def is_uuid(self):
        try:
            UUID(self.name, version=4)
        except (ValueError, IndexError):
            return False
        return True

    @property
    def is_resource(self):
        """The path is a resource if it is not a Collection

        :raises AbsPathRequired: path doesn't start with '/'
        """
        return not self.is_collection

    @property
    def is_collection(self):
        """The path is a Collection if there is only one part in the path. Be
        careful, the root is a Collection.

        :raises AbsPathRequired: path doesn't start with '/'
        """
        if not self.is_absolute():
            raise AbsPathRequired()
        return self.base == self.name

    def relative_to(self, path):
        try:
            return PurePosixPath.relative_to(self, path)
        except ValueError:
            return self


class classproperty(object):

    def __init__(self, f):
        self.f = f

    def __get__(self, instance, klass):
        if instance:
            try:
                return self.f(instance)
            except AttributeError:
                pass
        return self.f(klass)


def eventloop():
    # Allow to keep gevent greenlets running
    # while waiting for some input on the cli
    def inputhook(context):
        while not context.input_is_ready():
            gevent.sleep(0.1)

    return create_eventloop(inputhook=inputhook)


def continue_prompt(message=""):
    """Prompt the user to continue or not

    Returns True when the user type Yes.

    :param message: message to display
    :type message: str

    :rtype: bool
    """
    answer = False
    message = message + "\n'Yes' or 'No' to continue: "
    while answer not in ('Yes', 'No'):
        answer = prompt(message, eventloop=eventloop())
        if answer == "Yes":
            answer = True
            break
        if answer == "No":
            answer = False
            break
    return answer


def all_subclasses(cls):
    return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                   for g in all_subclasses(s)]


def to_json(resource_dict, cls=None):
    return json.dumps(resource_dict,
                      indent=2,
                      sort_keys=True,
                      skipkeys=True,
                      cls=cls)


def highlight_json(json_data):
    return highlight(json_data,
                     JsonLexer(indent=2),
                     Terminal256Formatter(bg="dark"))


def md5(fname):
    """Calculate md5sum of a file

    :param fname: file path
    :type fname: str
    """
    hash = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)
    return hash.hexdigest()


def to_unicode(value):
    if isinstance(value, string_types):
        return text_type(value)
    elif isinstance(value, collections.Mapping):
        return dict(map(to_unicode, list(value.items())))
    elif isinstance(value, collections.Iterable):
        return type(value)(map(to_unicode, value))
    return value


def printo(msg, encoding=None, errors='replace', std_type='stdout'):
    """Write msg on stdout. If no encoding is specified
    the detected encoding of stdout is used. If the encoding
    can't encode some chars they are replaced by '?'

    :param msg: message
    :type msg: unicode on python2 | str on python3
    """
    std = getattr(sys, std_type, sys.stdout)
    if encoding is None:
        try:
            encoding = std.encoding
        except:
            encoding = None
    # Fallback to ascii if no encoding is found
    if encoding is None:
        encoding = 'ascii'
    # https://docs.python.org/3/library/sys.html#sys.stdout
    # write in the binary buffer directly in python3
    if hasattr(std, 'buffer'):
        std = std.buffer
    std.write(msg.encode(encoding, errors=errors))
    std.write(b'\n')
    std.flush()


def format_table(rows, sep='  '):
    """Format table

    :param sep: separator between columns
    :type sep: unicode on python2 | str on python3

    Given the table::

        table = [
            ['foo', 'bar', 'foo'],
            [1, 2, 3],
            ['54a5a05d-c83b-4bb5-bd95-d90d6ea4a878'],
            ['foo', 45, 'bar', 2345]
        ]

    `format_table` will return::

        foo                                   bar  foo
        1                                     2    3
        54a5a05d-c83b-4bb5-bd95-d90d6ea4a878
        foo                                   45   bar  2345
    """
    max_col_length = [0] * 100
    # calculate max length for each col
    for row in rows:
        for index, (col, length) in enumerate(zip(row, max_col_length)):
            if len(text_type(col)) > length:
                max_col_length[index] = len(text_type(col))
    formated_rows = []
    for row in rows:
        format_str = sep.join([
            '{:<%s}' % l if i < (len(row) - 1) else '{}'
            for i, (c, l) in enumerate(zip(row, max_col_length))
        ])
        formated_rows.append(format_str.format(*row))
    return '\n'.join(formated_rows)


def format_tree(tree):
    """Format a python tree structure

    Given the python tree::

        tree = {
            'node': ['ROOT', 'This is the root of the tree'],
            'childs': [{
                'node': 'A1',
                'childs': [{
                    'node': 'B1',
                    'childs': [{
                        'node': 'C1'
                    }]
                },
                {
                    'node': 'B2'
                }]
            },
            {
                'node': 'A2',
                'childs': [{
                    'node': 'B3',
                    'childs': [{
                        'node': ['C2', 'This is a leaf']
                    },
                    {
                        'node': 'C3'
                    }]
                }]
            },
            {
                'node': ['A3', 'This is a node'],
                'childs': [{
                    'node': 'B2'
                }]
            }]
        }

    `format_tree` will return::

        ROOT            This is the root of the tree
        ├── A1
        │   ├── B1
        │   │   └── C1
        │   └── B2
        ├── A2
        │   └── B3
        │       ├── C2  This is a leaf
        │       └── C3
        └── A3          This is a node
            └── B2

    """

    def _traverse_tree(tree, parents=None):
        tree['parents'] = parents
        childs = tree.get('childs', [])
        nb_childs = len(childs)
        for index, child in enumerate(childs):
            child_parents = list(parents) + [index == nb_childs - 1]
            tree['childs'][index] = _traverse_tree(
                tree['childs'][index],
                parents=child_parents)
        return tree

    tree = _traverse_tree(tree, parents=[])

    def _get_rows_data(tree, rows):
        prefix = ''
        for p in tree['parents'][:-1]:
            if p is False:
                prefix += '│   '
            else:
                prefix += '    '
        if not tree['parents']:
            pass
        elif tree['parents'][-1] is True:
            prefix += '└── '
        else:
            prefix += '├── '
        if isinstance(tree['node'], string_types):
            tree['node'] = [tree['node']]
        rows.append([prefix + tree['node'][0]] + tree['node'][1:])
        for child in tree.get('childs', []):
            rows = _get_rows_data(child, rows)
        return rows

    rows = _get_rows_data(tree, [])
    return format_table(rows)


def parallel_map(func, iterable, args=None, kwargs=None, workers=None):
    """Map func on a list using gevent greenlets.

    :param func: function applied on iterable elements
    :type func: function
    :param iterable: elements to map the function over
    :type iterable: iterable
    :param args: arguments of func
    :type args: tuple
    :param kwargs: keyword arguments of func
    :type kwargs: dict
    :param workers: limit the number of greenlets
                    running in parrallel
    :type workers: int
    """
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}
    if workers is not None:
        pool = Pool(workers)
    else:
        pool = Group()
    iterable = [pool.spawn(func, i, *args, **kwargs) for i in iterable]
    pool.join(raise_error=True)
    for idx, i in enumerate(iterable):
        i_type = type(i.get())
        i_value = i.get()
        if issubclass(i_type, BaseException):
            raise i_value
        iterable[idx] = i_value
    return iterable
