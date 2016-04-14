# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
import tempfile
import inspect
import argparse
import pipes
import abc
from fnmatch import fnmatch
from collections import OrderedDict
from six import add_metaclass, text_type

from keystoneclient.exceptions import ClientException, HttpError

from pygments.token import Token

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import Completer, Completion

from .manager import CommandManager
from .resource import Resource
from .resource import Collection, RootCollection
from .client import ContrailAPISession
from .utils import Path, classproperty, continue_prompt, printo
from .style import default as default_style
from .exceptions import CommandError, CommandNotFound, BadPath, \
    ResourceNotFound, NoResourceFound


class ArgumentParser(argparse.ArgumentParser):

    def exit(self, status=0, message=None):
        raise CommandError(message or '')


class Arg(object):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def experimental(cls):
    old_call = cls.__call__

    def new_call(self, *args, **kwargs):
        print("This command is experimental. Use at your own risk.")
        old_call(self, *args, **kwargs)

    cls.__call__ = new_call
    return cls


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
    for path in paths:
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
                    result[r.path] = r
        elif ':' in path.name:
            try:
                r = Resource(path.base,
                             fq_name=path.name,
                             check=True)
                if predicate and not predicate(r):
                    continue
                result[r.path] = r
            except ResourceNotFound as e:
                raise BadPath(str(e))
        else:
            if path.is_resource:
                try:
                    r = Resource(path.base,
                                 uuid=path.name,
                                 check=True)
                    if predicate and not predicate(r):
                        continue
                    result[path] = r
                except ResourceNotFound as e:
                    raise BadPath(str(e))
            elif path.is_collection:
                c = Collection(path.base,
                               filters=filters,
                               parent_uuid=parent_uuid)
                if predicate and not predicate(c):
                    continue
                result[path] = c

    paths = list(result.values())
    if not paths:
        raise NoResourceFound()
    return paths


@add_metaclass(abc.ABCMeta)
class Command(object):
    """Base class for commands
    """
    description = ""
    """Description of the command"""
    aliases = []
    """Command aliases"""

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
    def arguments(cls):
        for attr, value in inspect.getmembers(cls):
            if isinstance(value, Arg):
                # Handle case for options
                # attr can't be something like '-r'
                if len(value.args) > 0:
                    attr = value.args[0]
                yield (attr, value.args[1:], value.kwargs)
        raise StopIteration()

    @classmethod
    def add_arguments_to_parser(cls, parser):
        for (arg_name, arg_args, arg_kwargs) in cls.arguments:
            parser.add_argument(arg_name, *arg_args, **arg_kwargs)

    def parse_and_call(self, *args):
        args = self.parser.parse_args(args=args)
        return self.__call__(**vars(args))

    @abc.abstractmethod
    def __call__(self, **kwargs):
        """Command must implement this method.

        The command must return an unicode string
        (unicode in python2 or str in python3)

        :param **kwargs: options of the command

        :rtype: unicode | str
        """


@experimental
class Rm(Command):
    description = "Delete a resource"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path')
    recursive = Arg("-r", "--recursive",
                    action="store_true", default=False,
                    help="Recursive delete of back_refs resources")
    force = Arg("-f", "--force",
                action="store_true", default=False,
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


class Actions:
    STORE = 'STORE'
    DELETE = 'DELETE'


class ResourceCompleter(Completer):
    """Resource completer for the shell command.

    The completer observe Resource created and deleted
    events to construct its list of resources available
    for completion.

    Completion can be done on uuid or fq_name.
    """
    def __init__(self):
        self.resources = {}
        self.trie = {}
        Resource.register('created', self._add_resource)
        Resource.register('deleted', self._del_resource)
        Collection.register('created', self._add_resource)
        Collection.register('deleted', self._del_resource)

    def _action_in_trie(self, value, path, action):
        v = ""
        for c in value:
            v += c
            if v not in self.trie:
                self.trie[v] = []
            if action == Actions.STORE:
                if path not in self.trie[v]:
                    self.trie[v].append(path)
                    self.trie[v].sort()
            elif action == Actions.DELETE:
                if path in self.trie[v]:
                    self.trie[v].remove(path)

    def _resource_action(self, resource, action):
        if action == Actions.STORE:
            self.resources[text_type(resource.path)] = resource
        elif action == Actions.DELETE and text_type(resource.path) in self.resources:
            self.resources.pop(text_type(resource.path))
        path_text_type = text_type(resource.path)
        for c in [path_text_type, text_type(resource.fq_name)]:
            self._action_in_trie(c, text_type(resource.path), action)

    def _add_resource(self, resource):
        self._resource_action(resource, Actions.STORE)

    def _del_resource(self, resource):
        self._resource_action(resource, Actions.DELETE)

    def get_completions(self, document, complete_event):
        path_before_cursor = document.get_word_before_cursor(WORD=True)

        searches = [
            # full path search
            text_type(Path(ShellContext.current_path, path_before_cursor)),
            # fq_name search
            path_before_cursor
        ]
        searches = [s for s in searches if s in self.trie]

        if not searches:
            return

        # limit list to 50 entries
        resources = [self.resources[p] for p in self.trie[searches[0]]][:50]

        for res in resources:
            rel_path = text_type(res.path.relative_to(ShellContext.current_path))
            if rel_path in ('.', '/', ''):
                continue
            yield Completion(text_type(rel_path),
                             -len(path_before_cursor),
                             display_meta=text_type(res.fq_name))


class ShellContext(object):
    current_path = Path("/")
    parent_uuid = None


class Shell(Command):
    description = "Run an interactive shell"
    parent_uuid = Arg('-P', '--parent-uuid',
                      help='Limit listing to parent_uuid',
                      default=None)

    def __call__(self, parent_uuid=None):

        def get_prompt_tokens(cli):
            return [
                (Token.Username, ContrailAPISession.user or ''),
                (Token.At, '@' if ContrailAPISession.user else ''),
                (Token.Host, ContrailAPISession.host),
                (Token.Colon, ':'),
                (Token.Path, str(ShellContext.current_path)),
                (Token.Pound, '> ')
            ]

        history = InMemoryHistory()
        completer = ResourceCompleter()
        commands = CommandManager()
        commands.load_namespace('contrail_api_cli.shell_command')
        ShellContext.parent_uuid = parent_uuid
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
                    ResourceNotFound, NoResourceFound, BadPath) as e:
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


class Set(Command):
    description = "Set or show shell options"
    option = Arg('-o', '--option')
    value = Arg(nargs='?',
                default=None,
                help='Option value')

    def __call__(self, option=None, value=None):
        if option and value:
            if option == 'current_path':
                value = Path(value)
            if value == 'None':
                value = None
            setattr(ShellContext, option, value)
        elif option:
            return text_type(getattr(ShellContext, option))
        else:
            output = []
            for option, value in inspect.getmembers(ShellContext,
                                                    lambda a: not(inspect.isroutine(a))):
                if not option.startswith('__'):
                    output.append('%s = %s' % (option, value))
            return "\n".join(output)


class Cd(Command):
    description = "Change resource context"
    path = Arg(nargs="?", help="Resource path", default='',
               metavar='path')

    def __call__(self, path=''):
        ShellContext.current_path = ShellContext.current_path / path


class Exit(Command):
    description = "Exit from cli"

    def __call__(self):
        raise EOFError


class Help(Command):

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
