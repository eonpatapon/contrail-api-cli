import sys
import inspect
import argparse
import pipes
import tempfile
from fnmatch import fnmatch
from collections import OrderedDict
from functools import reduce

from keystoneclient.exceptions import ClientException, HttpError

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory

from pygments import highlight
from pygments.token import Token
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter

from .resource import ResourceEncoder, Resource, Collection, RootCollection, ResourceCompleter
from .client import to_json, ContrailAPISession
from .utils import ShellContext, Path, classproperty, all_subclasses, continue_prompt
from .style import PromptStyle


class CommandNotFound(Exception):
    pass


class CommandError(Exception):
    pass


class ArgumentParser(argparse.ArgumentParser):

    def exit(self, status=0, message=None):
        print(message)
        raise CommandError()


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


class BadPath(Exception):
    pass


def expand_paths(paths=None):
    """Return an unique list of resources or collections from a list of paths.
    Supports fq_name and wilcards resolution.

    >>> expand_paths(['virtual-network', 'floating-ip/2a0a54b4-a420-485e-8372-42f70a627ec9'])
    [Collection('virtual-network'), Resource('floating-ip', uuid='2a0a54b4-a420-485e-8372-42f70a627ec9')]

    @param paths: list of paths relative to the current path
                  that may contain wildcards (*, ?) or fq_names
    @type paths: [str]
    @rtype: [Resource|Collection]
    @raises BadPath: path cannot be resolved
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
                col = RootCollection(fetch=True)
            else:
                col = Collection(path.base, fetch=True)
            for r in col:
                if (fnmatch(str(r.path), str(path)) or
                        fnmatch(str(Path("/", r.type, r.fq_name)), str(path))):
                    result[r.path] = r
        elif ':' in path.name:
            try:
                r = Resource(path.base, fq_name=path.name)
                result[r.path] = r
            except TypeError as e:
                raise BadPath("Bad fq name format for in %s" % path)
            except ValueError as e:
                raise BadPath(str(e))
        else:
            if path.is_resource:
                try:
                    result[path] = Resource(path.base, uuid=path.name, check_uuid=True)
                except ValueError as e:
                    raise BadPath(str(e))
            elif path.is_collection:
                result[path] = Collection(path.base)
    return list(result.values())


class RelativeResourceEncoder(ResourceEncoder):

    def default(self, obj):
        if isinstance(obj, Path):
            return str(obj.relative_to(ShellContext.current_path))
        return super(RelativeResourceEncoder, self).default(obj)


class BaseCommand(object):
    description = ""
    aliases = []

    def __init__(self):
        self.parser = ArgumentParser(prog=self.name,
                                     description=self.description)
        self.add_arguments_to_parser(self.parser)
        self._is_piped = False

    @classproperty
    def name(cls):
        return cls.__name__.lower()

    def current_path(self, resource):
        """Return current path for resource

        @param resource: resource or collection
        @type resource: Resource|Collection

        @rtype: str
        """
        return str(resource.path.relative_to(ShellContext.current_path))

    @property
    def is_piped(self):
        """Return True if the command result is beeing piped
        to another command.

        @rtype: bool
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


class Command(BaseCommand):
    """ Class for commands that can be used outside the shell
    """
    pass


class ShellCommand(BaseCommand):
    """ Class for commands used only in the shell
    """
    pass


class Ls(Command):
    description = "List resource objects"
    paths = Arg(nargs="*", help="Resource path(s)")
    aliases = ['ll']

    def __call__(self, paths=None):
        try:
            resources = expand_paths(paths)
        except BadPath as e:
            raise CommandError(str(e))
        result = []
        for r in resources:
            if isinstance(r, Collection):
                r.fetch()
                result += [self.current_path(i) for i in r]
            elif isinstance(r, Resource):
                result.append(self.current_path(r))
            else:
                raise CommandError('Not a resource or collection')
        return "\n".join(result)


class Cat(Command):
    description = "Print a resource"
    paths = Arg(nargs="*", help="Resource path(s)")

    def colorize(self, json_data):
        return highlight(json_data,
                         JsonLexer(indent=2),
                         Terminal256Formatter(bg="dark"))

    def __call__(self, paths=None):
        try:
            resources = expand_paths(paths)
        except BadPath as e:
            raise CommandError(str(e))
        if not resources:
            raise CommandError('No resource given')
        result = []
        for r in resources:
            if not isinstance(r, Resource):
                raise CommandError('%s is not a resource' % self.current_path(r))
            r.fetch()
            json_data = to_json(r.data, cls=RelativeResourceEncoder)
            if self.is_piped:
                result.append(json_data)
            else:
                result.append(self.colorize(json_data))
        return "".join(result)


class Count(Command):
    description = "Count number of resources"
    paths = Arg(nargs="*", help="Resource path(s)")

    def __call__(self, paths=None):
        try:
            collections = expand_paths(paths)
        except BadPath as e:
            raise CommandError(str(e))
        if not collections:
            raise CommandError('No collection given')
        result = []
        for c in collections:
            if not isinstance(c, Collection):
                raise CommandError('%s is not a collection' % self.current_path(c))
            result.append(str(len(c)))
        return "\n".join(result)


@experimental
class Rm(Command):
    description = "Delete a resource"
    paths = Arg(nargs="*", help="Resource path(s)")
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
        try:
            resources = expand_paths(paths)
        except BadPath as e:
            raise CommandError(str(e))
        for r in resources:
            if not isinstance(r, Resource):
                raise CommandError('%s is not a resource' % self.current_path(r))
        if not resources:
            raise CommandError("No resource to delete")
        if recursive:
            resources = self._get_back_refs(resources, [])
        if resources:
            message = """About to delete:
 - %s""" % "\n - ".join([self.current_path(r) for r in resources])
            if force or continue_prompt(message=message):
                for r in reversed(resources):
                    print("Deleting %s" % self.current_path(r))
                    try:
                        r.delete()
                    except HttpError as e:
                        raise CommandError("Failed to delete resource: %s" % str(e))


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

        history = InMemoryHistory()
        completer = ResourceCompleter()
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
                cmd = get_command(action[0])
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
                print(e)
                continue
            try:
                result = cmd.parse_and_call(*args)
            except (HttpError, ClientException, CommandError) as e:
                print(e)
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
                    print(t.read().strip())
                else:
                    print(result.strip())


class Cd(ShellCommand):
    description = "Change resource context"
    path = Arg(nargs="?", help="Resource path", default='')

    def __call__(self, path=''):
        ShellContext.current_path = ShellContext.current_path / path


class Exit(ShellCommand):
    description = "Exit from cli"

    def __call__(self):
        raise EOFError


class Help(ShellCommand):

    def __call__(self):
        return "Available commands: %s" % " ".join([c.name for c in all_commands_list()])


def make_api_session(options):
    ContrailAPISession.make(options.os_auth_plugin,
                            **vars(options))


def all_commands_list():
    return commands_list() + shell_commands_list()


def commands_list():
    return all_subclasses(Command)


def shell_commands_list():
    return all_subclasses(ShellCommand)


def get_command(name):
    """Return command instance from name

    @param name: name or alias of command
    @type name: str

    @rtype: Command|ShellCommand
    @raise: CommandNotFound
    """
    cmd = reduce(lambda a, c: c if c.name == name or name in c.aliases else a,
                 all_commands_list(), None)
    if cmd is None:
        raise CommandNotFound('Command %s not found. Type help for all commands' % name)
    return cmd()
