# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
import inspect
import argparse
import abc
from fnmatch import fnmatch
from collections import OrderedDict
from six import add_metaclass, text_type

from .resource import Resource
from .resource import Collection, RootCollection
from .schema import ResourceNotDefined
from .utils import Path, classproperty, parallel_map
from .exceptions import CommandError, NotFound
from .context import Context


class ArgumentParser(argparse.ArgumentParser):

    def exit(self, status=0, message=None):
        raise CommandError(message or '')


class BaseOption(object):
    _creation_idx = 0

    def __init__(self, *args, **kwargs):
        self.attr = ''
        self.complete = None
        if 'complete' in kwargs:
            self.complete = kwargs.pop('complete')
        self.kwargs = kwargs
        # keep track of options order
        self._creation_idx = BaseOption._creation_idx
        BaseOption._creation_idx += 1

    @property
    def help(self):
        return self.kwargs.get('help', '') % self.kwargs

    @property
    def dest(self):
        return self.kwargs.get('get', self.attr)

    @property
    def is_multiple(self):
        return self.kwargs.get('nargs') in ('*', '+') or \
            self.kwargs.get('action') in ('append',)

    @property
    def nargs(self):
        if self.kwargs.get('nargs') == '?':
            return 1
        return self.kwargs.get('nargs', 1)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.attr)


class Option(BaseOption):

    def __init__(self, short_name=None, **kwargs):
        BaseOption.__init__(self, **kwargs)
        self.short_name = short_name

    @property
    def need_value(self):
        return self.kwargs.get('action') not in ('store_true', 'store_false')

    @property
    def long_name(self):
        return '--%s' % self.attr.replace('_', '-')

    @property
    def option_strings(self):
        return [n for n in (self.long_name, self.short_name) if n is not None]


class Arg(BaseOption):
    pass


def experimental(cls):
    old_call = cls.__call__

    def new_call(self, *args, **kwargs):
        print("This command is experimental. Use at your own risk.")
        old_call(self, *args, **kwargs)

    cls.__call__ = new_call
    return cls


def _path_to_resources(path, predicate=None, filters=None, parent_uuid=None):
    if any([c in text_type(path) for c in ('*', '?')]):
        if any([c in path.base for c in ('*', '?')]):
            col = RootCollection(fetch=True,
                                 filters=filters,
                                 parent_uuid=parent_uuid)
        else:
            col = Collection(path.base, fetch=True,
                             filters=filters,
                             parent_uuid=parent_uuid)
        for r in col:
            if predicate and not predicate(r):
                continue
            # list of paths to match against
            paths = [r.path,
                     Path('/', r.type, text_type(r.fq_name))]
            if any([fnmatch(text_type(p), text_type(path)) for p in paths]):
                yield r
    elif path.is_resource:
        if path.is_uuid:
            kwargs = {'uuid': path.name}
        else:
            kwargs = {'fq_name': path.name}
        try:
            r = Resource(path.base,
                         check=True,
                         **kwargs)
        except ResourceNotDefined as e:
            raise CommandError(text_type(e))
        if predicate and not predicate(r):
            raise StopIteration
        yield r
    elif path.is_collection:
        c = Collection(path.base,
                       filters=filters,
                       parent_uuid=parent_uuid)
        if predicate and not predicate(c):
            raise StopIteration
        yield c


def expand_paths(paths=None, predicate=None, filters=None, parent_uuid=None):
    """Return an unique list of resources or collections from a list of paths.
    Supports fq_name and wilcards resolution.

    >>> expand_paths(['virtual-network',
                      'floating-ip/2a0a54b4-a420-485e-8372-42f70a627ec9'])
    [Collection('virtual-network'),
     Resource('floating-ip', uuid='2a0a54b4-a420-485e-8372-42f70a627ec9')]

    :param paths: list of paths relative to the current path
                  that may contain wildcards (*, ?) or fq_names
    :type paths: [str]
    :param predicate: function to filter found resources
    :type predicate: f(resource) -> bool
    :param filters: list of filters for Collections
    :type filters: [(name, value), ...]
    :rtype: [Resource or Collection]
    :raises BadPath: path cannot be resolved
    """
    if not paths:
        paths = [Context().shell.current_path]
    else:
        paths = [Context().shell.current_path / res for res in paths]

    # use a dict to have unique paths
    # but keep them ordered
    result = OrderedDict()
    for res in parallel_map(_path_to_resources, paths,
                            kwargs={'predicate': predicate,
                                    'filters': filters,
                                    'parent_uuid': parent_uuid},
                            workers=50):
        for r in res:
            result[r.path] = r

    resources = list(result.values())
    if not resources:
        raise NotFound()
    return resources


@add_metaclass(abc.ABCMeta)
class Command(object):
    """Base class for commands
    """
    description = ""
    """Description of the command"""
    aliases = []
    """Command aliases"""
    _options = None
    _args = None

    def __init__(self, name):
        self.parser = ArgumentParser(prog=name, description=self.description)
        self.add_arguments_to_parser(self.parser)
        self._is_piped = False

    def current_path(self, resource):
        """Return current path for resource

        :param resource: resource or collection
        :type resource: Resource|Collection

        :rtype: str
        """
        return text_type(resource.path.relative_to(Context().shell.current_path))

    @property
    def is_piped(self):
        """Return True if the command result is beeing piped
        to another command.

        :rtype: bool
        """
        return not sys.stdout.isatty() or self._is_piped

    @is_piped.setter
    def is_piped(self, value):
        self._is_piped = value

    @classproperty
    def options(cls):
        if cls._options is not None:
            return cls._options
        cls._options = OrderedDict()
        for attr, option in sorted(
                inspect.getmembers(cls, lambda o: isinstance(o, Option)),
                key=lambda i: i[1]._creation_idx):
            option.attr = attr
            cls._options[text_type(attr)] = option
        return cls._options

    @classproperty
    def args(cls):
        if cls._args is not None:
            return cls._args
        cls._args = OrderedDict()
        for attr, arg in sorted(
                inspect.getmembers(cls, lambda o: isinstance(o, Arg)),
                key=lambda i: i[1]._creation_idx):
            arg.attr = attr
            cls._args[text_type(attr)] = arg
        return cls._args

    @classmethod
    def add_arguments_to_parser(cls, parser):
        for (arg_name, arg) in cls.args.items():
            parser.add_argument(arg_name, **arg.kwargs)
        for (option_name, option) in cls.options.items():
            parser.add_argument(*option.option_strings, **option.kwargs)

    def parse_and_call(self, *args):
        args = self.parser.parse_args(args=args)
        return self.__call__(**vars(args))

    @abc.abstractmethod
    def __call__(self, **kwargs):
        """Command must implement this method.

        The command must return an unicode string
        (unicode in python2 or str in python3)

        :param kwargs: options of the command

        :rtype: unicode | str
        """
