# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import copy
import os
import sys
import tempfile
import inspect
import argparse
import pipes
import subprocess
import json
import abc
from fnmatch import fnmatch
from collections import OrderedDict
from six import b, add_metaclass, text_type
try:
    from functools import reduce
except ImportError:
    pass

from keystoneclient.exceptions import ClientException, HttpError

from tabulate import tabulate

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import Completer, Completion

from pygments import highlight
from pygments.token import Token
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter

from .manager import CommandManager
from .resource import Resource
from .resource import Collection, RootCollection
from .client import ContrailAPISession
from .utils import Path, classproperty, continue_prompt, md5, printo
from .style import PromptStyle
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


class Ls(Command):
    description = "List resource objects"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path')
    long = Arg('-l', '--long',
               default=False, action="store_true",
               help="use a long listing format")
    fields = Arg('-c', '--column', action="append",
                 help="fields to show in long mode",
                 default=[], dest="fields",
                 metavar="field_name")
    filters = Arg('-f', '--filter', action="append",
                  help="filter predicate",
                  default=[], dest='filters',
                  metavar='field_name=field_value')
    parent_uuid = Arg('-p', '--parent_uuid',
                      help="Filter by parent uuid")
    # fields to show in -l mode when no
    # column is specified
    default_fields = [u'fq_name']
    aliases = ['ll']

    def _field_val_to_str(self, fval, fkey=None):
        if fkey in ('fq_name', 'to'):
            return ":".join(fval)
        elif isinstance(fval, list) or isinstance(fval, Collection):
            return ",".join([self._field_val_to_str(i) for i in fval])
        elif isinstance(fval, dict) or isinstance(fval, Resource):
            return "|".join(["%s=%s" % (k, self._field_val_to_str(v, k))
                             for k, v in fval.items()])
        return str(fval)

    def _get_field(self, resource, field):
        # elif field.startswith('.'):
            # value = jq(field).transform(resource.json())
        value = '_'
        if field == 'path':
            value = self.current_path(resource)
        elif hasattr(resource, field):
            value = getattr(resource, field)
        elif isinstance(resource, Resource):
            value = resource.get(field, '_')
        return self._field_val_to_str(value)

    def _get_filter(self, predicate):
        # parse input predicate
        try:
            name, value = predicate.split('=')
        except ValueError:
            raise CommandError('Invalid filter predicate %s. '
                               'Use name=value format.' % predicate)
        if value == 'False':
            value = False
        elif value == 'True':
            value = True
        elif value == 'None':
            value = None
        else:
            try:
                value = int(value)
            except ValueError:
                value = str(value)
        return (name, value)

    def __call__(self, paths=None, long=False, fields=None,
                 filters=None, parent_uuid=None):
        if not long:
            fields = []
        elif not fields:
            fields = self.default_fields
        if filters:
            filters = [self._get_filter(p) for p in filters]
        if not parent_uuid:
            parent_uuid = ShellContext.parent_uuid
        resources = expand_paths(paths, filters=filters,
                                 parent_uuid=parent_uuid)
        result = []
        for r in resources:
            if isinstance(r, Collection):
                r.fetch(fields=fields)
                result += r.data
            elif isinstance(r, Resource):
                # need to fetch the resource to get needed fields
                if len(fields) > 1 or 'fq_name' not in fields:
                    r.fetch()
                result.append(r)
            else:
                raise CommandError('Not a resource or collection')
        # retrieve asked fields for each resource
        fields = ['path'] + fields
        result = [[self._get_field(r, f) for f in fields] for r in result]
        return tabulate(result, tablefmt='plain')


class Cat(Command):
    description = "Print a resource"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path')

    def colorize(self, json_data):
        return highlight(json_data,
                         JsonLexer(indent=2),
                         Terminal256Formatter(bg="dark"))

    def __call__(self, paths=None):
        resources = expand_paths(paths,
                                 predicate=lambda r: isinstance(r, Resource))
        result = []
        for r in resources:
            r.fetch()
            json_data = r.json()
            if self.is_piped:
                result.append(json_data)
            else:
                result.append(self.colorize(json_data))
        return "".join(result)


class Count(Command):
    description = "Count number of resources"
    paths = Arg(nargs="*", help="Resource path(s)")

    def __call__(self, paths=None):
        collections = expand_paths(paths,
                                   predicate=lambda r: isinstance(r, Collection))
        result = []
        for c in collections:
            result.append(str(len(c)))
        return "\n".join(result)


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


@experimental
class Edit(Command):
    description = "Edit resource"
    path = Arg(nargs="?", help="Resource path", default='')
    template = Arg('-t', '--template',
                   help="Create new resource from existing",
                   action="store_true", default=False)
    aliases = ['vim', 'emacs', 'nano']

    def __call__(self, path='', template=False):
        resources = expand_paths([path],
                                 predicate=lambda r: isinstance(r, Resource))
        if len(resources) > 1:
            raise CommandError("Can't edit multiple resources")
        resource = resources[0]
        # don't show childs or back_refs
        resource.fetch(exclude_children=True, exclude_back_refs=True)
        resource.pop('id_perms')
        if template:
            resource.pop('href')
            resource.pop('uuid')
        editor = os.environ.get('EDITOR', 'vim')
        with tempfile.NamedTemporaryFile(suffix='tmp.json') as tmp:
            tmp.write(b(resource.json()))
            tmp.flush()
            tmp_md5 = md5(tmp.name)
            subprocess.call([editor, tmp.name])
            tmp.seek(0)
            if tmp_md5 == md5(tmp.name):
                print("No modification made, doing nothing...")
                return
            data_json = tmp.read().decode('utf-8')
        try:
            data = json.loads(data_json)
        except ValueError as e:
            raise CommandError('Provided JSON is not valid: ' + str(e))
        if template:
            # create new resource
            resource = Resource(resource.type, **data)
        else:
            resource.update(data)
        resource.save()


class Tree(Command):
    description = "Tree of resource references"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path')
    reverse = Arg('-r', '--reverse',
                  help="Show tree of back references",
                  action="store_true", default=False)
    parent = Arg('-p', '--parent',
                 help="Show tree of parents",
                 action="store_true", default=False)

    def _get_tree(self, resource, tree, parent_path=None, reverse=False, parent=False):
        if parent:
            try:
                refs = [resource.parent]
            except ResourceNotFound:
                refs = []
        elif reverse:
            refs = list(resource.back_refs)
        else:
            refs = list(resource.refs)
        nb_refs = len(refs)
        for idx, ref in enumerate(refs):
            # avoid refs loops (parent -> ref -> parent)
            if str(ref.path) in parent_path:
                continue
            ref.fetch()
            tree['childs'][str(ref.path)] = {
                'index': idx + 1,
                'len': nb_refs,
                'level': tree['level'] + 1,
                'childs': OrderedDict(),
                'parents': copy.copy(tree['parents']),
                'meta': str(ref.fq_name)
            }
            if tree['len'] == tree['index']:
                tree['childs'][str(ref.path)]['parents'].append(0)
            else:
                tree['childs'][str(ref.path)]['parents'].append(1)

            self._get_tree(ref, tree['childs'][str(ref.path)],
                           parent_path=str(resource.path),
                           reverse=reverse, parent=parent)

    def _get_rows(self, tree, rows):
        for idx, (path, infos) in enumerate(tree.items()):
            col = ''

            for parent in infos['parents'][1:]:
                if parent == 1:
                    col += '│   '
                else:
                    col += '    '

            if infos['level'] == 0:
                col += ''
            elif infos['index'] == infos['len']:
                col += '└── '
            else:
                col += '├── '

            col += path
            rows.append((col, infos['meta']))
            self._get_rows(infos['childs'], rows)
        return rows

    def __call__(self, paths=None, reverse=False, parent=False):
        resources = expand_paths(paths,
                                 predicate=lambda r: isinstance(r, Resource))
        for resource in resources:
            resource.fetch()
            tree = {
                str(resource.path): {
                    'level': 0,
                    'index': 1,
                    'len': 1,
                    'childs': OrderedDict(),
                    'parents': [],
                    'meta': str(resource.fq_name)
                }
            }
            self._get_tree(resource, tree[str(resource.path)],
                           parent_path=str(resource.path),
                           reverse=reverse, parent=parent)
            rows = self._get_rows(tree, [])
            max_path_length = reduce(lambda a, r: len(r[0]) if len(r[0]) > a else a,
                                     rows, 0)

            def format_row(path, fq_name):
                return path + ' ' * (max_path_length - len(path)) + '  ' + fq_name

            return "\n".join([format_row(p, f) for p, f in rows])


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
    parent_uuid = Arg('-p', '--parent_uuid',
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
        if parent_uuid is None:
            print('Warning: no parent_uuid specified. ls command will list '
                  'resources of all parents by default. See set --help to '
                  'set parent_uuid or start the shell with the --parent_uuid '
                  'option.')
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
                                style=PromptStyle)
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


def make_api_session(options):
    ContrailAPISession.make(options.os_auth_plugin,
                            **vars(options))
