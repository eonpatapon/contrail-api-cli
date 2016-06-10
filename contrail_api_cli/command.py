# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os.path
import sys
import tempfile
import inspect
import argparse
import pipes
import abc
import re
from fnmatch import fnmatch
from collections import OrderedDict
from six import add_metaclass, text_type

from keystoneclient.exceptions import ClientException, HttpError

from pygments.token import Token

from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import Completer, Completion

from .manager import CommandManager
from .resource import Resource, ResourceCache
from .resource import Collection, RootCollection
from .client import ContrailAPISession
from .utils import CONFIG_DIR, Path, classproperty, continue_prompt, printo, parallel_map
from .style import default as default_style
from .exceptions import CommandError, CommandNotFound, \
    NotFound, Exists, CommandInvalid
from .parser import CommandParser


class ArgumentParser(argparse.ArgumentParser):

    def exit(self, status=0, message=None):
        raise CommandError(message or '')


class BaseOption(object):

    def __init__(self, *args, **kwargs):
        self.attr = ''

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


class Option(BaseOption):

    def __init__(self, short_name=None, **kwargs):
        BaseOption.__init__(self)
        self.short_name = short_name
        self.kwargs = kwargs

    @property
    def long_name(self):
        return '--%s' % self.attr.replace('_', '-')

    @property
    def option_strings(self):
        return [n for n in (self.long_name, self.short_name) if n is not None]


class Arg(BaseOption):

    def __init__(self, **kwargs):
        BaseOption.__init__(self)
        self.kwargs = kwargs


def experimental(cls):
    old_call = cls.__call__

    def new_call(self, *args, **kwargs):
        print("This command is experimental. Use at your own risk.")
        old_call(self, *args, **kwargs)

    cls.__call__ = new_call
    return cls


def _path_to_resources(path, predicate=None, filters=None, parent_uuid=None):
    if any([c in str(path) for c in ('*', '?')]):
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
                     Path('/', r.type, str(r.fq_name))]
            if any([fnmatch(str(p), str(path)) for p in paths]):
                yield r
    elif path.is_resource:
        if path.is_uuid:
            kwargs = {'uuid': path.name}
        else:
            kwargs = {'fq_name': path.name}
        r = Resource(path.base,
                     check=True,
                     **kwargs)
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
        paths = [ShellContext.current_path]
    else:
        paths = [ShellContext.current_path / res for res in paths]

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
        return str(resource.path.relative_to(ShellContext.current_path))

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
        for attr, option in inspect.getmembers(cls):
            if isinstance(option, Option):
                option.attr = attr
                cls._options[text_type(attr)] = option
        return cls._options

    @classproperty
    def args(cls):
        if cls._args is not None:
            return cls._args
        cls._args = OrderedDict()
        for attr, arg in inspect.getmembers(cls):
            if isinstance(arg, Arg):
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


@experimental
class Rm(Command):
    description = "Delete a resource"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path')
    recursive = Option("-r", action="store_true",
                       default=False,
                       help="Recursive delete of back_refs resources")
    force = Option("-f", action="store_true",
                   default=False,
                   help="Don't ask for confirmation")

    def _get_back_refs(self, resources, back_refs):
        for resource in resources:
            resource.fetch()
            if resource in back_refs:
                back_refs.remove(resource)
            back_refs.append(resource)
            for back_ref in resource.back_refs:
                back_refs = self._get_back_refs([back_ref], back_refs)
        return back_refs

    def __call__(self, paths=None, recursive=False, force=False):
        resources = expand_paths(paths,
                                 predicate=lambda r: isinstance(r, Resource))
        if recursive:
            resources = self._get_back_refs(resources, [])
        if resources:
            message = """About to delete:
 - %s""" % "\n - ".join([self.current_path(r) for r in resources])
            if force or continue_prompt(message=message):
                for r in reversed(resources):
                    print("Deleting %s" % self.current_path(r))
                    r.delete()


class ShellCompleter(Completer):

    def __init__(self, aliases=None):
        self.mgr = CommandManager()
        self.cache = ResourceCache()
        self.aliases = aliases or ShellAliases()

    def get_completions(self, document, complete_event):
        text_before_cursor = document.get_word_before_cursor(WORD=True)
        text = self.aliases.apply(document.text)

        try:
            parser = CommandParser(text)
            # complete options for the current command
            if text_before_cursor.startswith('-'):
                for option in parser.available_options:
                    option_name = option.short_name or option.long_name
                    if text_before_cursor.startswith('--'):
                        option_name = option.long_name
                    if option_name.startswith(text_before_cursor):
                        yield Completion(option_name,
                                         -len(text_before_cursor),
                                         display_meta=option.help)
                raise StopIteration
        except CommandNotFound:
            for cmd_name, cmd in self.mgr.list:
                if cmd_name.startswith(text_before_cursor):
                    yield Completion(cmd_name,
                                     -len(text_before_cursor),
                                     display_meta=cmd.description)
            raise StopIteration
        except CommandInvalid:
            raise StopIteration

        # resource completion from cache
        searches = [
            # full path search
            text_type(Path(ShellContext.current_path, text_before_cursor)),
            # fq_name search
            text_before_cursor
        ]
        # limit list to 50 entries
        resources = self.cache.search(searches, limit=50)
        for res in resources:
            rel_path = text_type(res.path.relative_to(ShellContext.current_path))
            if rel_path in ('.', '/', ''):
                continue
            yield Completion(text_type(rel_path),
                             -len(text_before_cursor),
                             display_meta=text_type(res.fq_name))


class ShellContext(object):
    current_path = Path("/")


class ShellAliases(object):

    def __init__(self):
        self._aliases = {}

    def set(self, alias):
        if '=' not in alias:
            raise CommandError('Alias %s is incorrect' % alias)
        alias, cmd = alias.split('=')
        self._aliases[alias.strip()] = cmd.strip()

    def apply(self, cmd):
        cmd = re.split(r'(\s+)', cmd)
        cmd = [self._aliases.get(c, c) for c in cmd]
        return ' '.join(cmd)


class Shell(Command):
    description = "Run an interactive shell"

    def __call__(self):

        def get_prompt_tokens(cli):
            return [
                (Token.Username, ContrailAPISession.user or ''),
                (Token.At, '@' if ContrailAPISession.user else ''),
                (Token.Host, ContrailAPISession.host),
                (Token.Colon, ':'),
                (Token.Path, str(ShellContext.current_path)),
                (Token.Pound, '> ')
            ]

        history = FileHistory(os.path.join(CONFIG_DIR, 'history'))
        commands = CommandManager()
        commands.load_namespace('contrail_api_cli.shell_command')
        aliases = ShellAliases()
        for cmd_name, cmd in commands.list:
            map(aliases.set, cmd.aliases)
        completer = ShellCompleter(aliases=aliases)
        # load home resources
        try:
            RootCollection(fetch=True)
        except ClientException as e:
            return str(e)

        while True:
            try:
                action = prompt(get_prompt_tokens=get_prompt_tokens,
                                history=history,
                                completer=completer,
                                style=default_style)
                action = aliases.apply(action)
            except (EOFError, KeyboardInterrupt):
                break
            try:
                action = action.split('|')
                pipe_cmds = action[1:]
                action = action[0].split()
                cmd = commands.get(action[0])
                args = action[1:]
                if pipe_cmds:
                    p = pipes.Template()
                    for pipe_cmd in pipe_cmds:
                        p.append(str(pipe_cmd.strip()), '--')
                    cmd.is_piped = True
                else:
                    cmd.is_piped = False
            except IndexError:
                continue
            except CommandNotFound as e:
                printo(text_type(e))
                continue
            try:
                result = cmd.parse_and_call(*args)
            except (HttpError, ClientException, CommandError,
                    NotFound, Exists) as e:
                printo(text_type(e))
                continue
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            else:
                if not result:
                    continue
                elif pipe_cmds:
                    t = tempfile.NamedTemporaryFile('r')
                    with p.open(t.name, 'w') as f:
                        f.write(result)
                    printo(t.read().strip())
                else:
                    printo(result)


class Cd(Command):
    description = "Change resource context"
    path = Arg(nargs="?", help="Resource path", default='',
               metavar='path')

    def __call__(self, path=''):
        ShellContext.current_path = ShellContext.current_path / path


class Exit(Command):
    description = "Exit from shell"

    def __call__(self):
        raise EOFError


class Help(Command):
    description = "List all available commands"

    def __call__(self):
        commands = CommandManager()
        return "Available commands: %s" % " ".join(
            [name for name, cmd in commands.list])


class Python(Command):
    description = 'Run a python interpreter'

    def __call__(self):
        try:
            from ptpython.repl import embed
            embed(globals(), None)
        except ImportError:
            try:
                from IPython import embed
                embed()
            except ImportError:
                import code
                code.interact(banner="Launching standard python repl", readfunc=None, local=globals())


def make_api_session(options):
    ContrailAPISession.make(options.os_auth_plugin,
                            **vars(options))
