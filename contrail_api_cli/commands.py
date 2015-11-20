import inspect
import argparse
from fnmatch import fnmatch

from keystoneclient.exceptions import HttpError

from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter

from .resource import ResourceEncoder, Resource, Collection
from .client import to_json
from .utils import ShellContext, Path, classproperty, all_subclasses, continue_prompt


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


def expand_resources(resources):
    """Return a list of paths from a list of resources in the cli

    @param resources: list of resources relative to the current path
                      that may contain wildcards (*, ?)
    @type resources: [str]
    @rtype: [Path]
    """
    if resources is None:
        paths = [ShellContext.current_path]
    else:
        paths = [ShellContext.current_path / res for res in resources]

    result = []
    for path in paths:
        if any([c in str(path) for c in ('*', '?')]):
            col = Collection(path.base, fetch=True)
            result += ([r.path for r in col
                        if fnmatch(str(r.path), str(path))])
        else:
            result.append(path)
    return result


class RelativeResourceEncoder(ResourceEncoder):

    def default(self, obj):
        if isinstance(obj, Path):
            return str(obj.relative_to(ShellContext.current_path))
        return super(RelativeResourceEncoder, self).default(obj)


class BaseCommand(object):
    description = ""

    def __init__(self):
        self.parser = ArgumentParser(prog=self.name,
                                     description=self.description)
        self.add_arguments_to_parser(self.parser)

    @classproperty
    def name(cls):
        return cls.__name__.lower()

    @classmethod
    def add_arguments_to_parser(cls, parser):
        for attr, value in inspect.getmembers(cls):
            if isinstance(value, Arg):
                # Handle case for options
                # attr can't be something like '-r'
                if len(value.args) > 0:
                    attr = value.args[0]
                    value.args = value.args[1:]
                parser.add_argument(attr, *value.args, **value.kwargs)

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
    resource = Arg(nargs="?", help="Resource path", default="")

    def colorize(self, json_data):
        return highlight(json_data,
                         JsonLexer(indent=2),
                         Terminal256Formatter(bg="dark"))

    def __call__(self, resource=''):
        path = ShellContext.current_path / resource
        # Find Path from fq_name
        if ":" in resource:
            try:
                return Resource(path.base, fq_name=path.name, fetch=True)
            except ValueError as e:
                return str(e)
        else:
            if path.is_collection or path.is_root:
                return "\n".join([str(i.path.relative_to(ShellContext.current_path))
                                  for i in Collection(path.base, fetch=True)])
            elif path.is_resource:
                res = Resource(path.base, uuid=path.name, fetch=True)
                json_data = to_json(res.data, cls=RelativeResourceEncoder)
                return self.colorize(json_data)
        return "Not a resource"


class Cat(Command):
    description = "Print a resource"
    resource = Arg(nargs="?", help="Resource path", default="")

    def __call__(self, resource=''):
        ShellContext.current_path = ShellContext.current_path / resource


class Count(Command):
    description = "Count number of resources"
    resource = Arg(nargs="?", help="Resource path", default='')

    def __call__(self, resource=''):
        path = ShellContext.current_path / resource
        if path.is_collection:
            return len(Collection(path.base))


@experimental
class Rm(Command):
    description = "Delete a resource"
    resource = Arg(nargs="*", help="Resource path", default=[])
    recursive = Arg("-r", "--recursive", dest="recursive",
                    action="store_true", default=False,
                    help="Recursive delete of back_refs resources")
    force = Arg("-f", "--force", dest="force",
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

    def __call__(self, resource=None, recursive=False, force=False):
        paths = expand_resources(resource)
        resources = list(set([Resource(p.base, uuid=p.name) for p in paths if p.is_resource]))
        if not resources:
            print("Can't match any resource to delete.")
        if recursive:
            resources = self._get_back_refs(resources, [])
        if resources:
            message = """About to delete:
 - %s""" % "\n - ".join([str(r.path.relative_to(ShellContext.current_path))
                        for r in resources])
            if force or continue_prompt(message=message):
                for r in reversed(resources):
                    print("Deleting %s" % str(r.path.relative_to(ShellContext.current_path)))
                    try:
                        r.delete()
                    except HttpError as e:
                        raise CommandError("Failed to delete resource: %s" % str(e))


class Cd(ShellCommand):
    description = "Change resource context"
    resource = Arg(nargs="?", help="Resource path", default='')

    def __call__(self, resource=''):
        ShellContext.current_path = ShellContext.current_path / resource


class Exit(ShellCommand):
    description = "Exit from cli"

    def __call__(self):
        raise EOFError


class Help(ShellCommand):

    def __call__(self):
        return "Available commands: %s" % " ".join([c.name for c in all_commands_list()])


def all_commands_list():
    return commands_list() + shell_commands_list()


def commands_list():
    return all_subclasses(Command)


def shell_commands_list():
    return all_subclasses(ShellCommand)


ls = ll = Ls()
cd = Cd()
help = Help()
count = Count()
rm = Rm()
exit = Exit()
