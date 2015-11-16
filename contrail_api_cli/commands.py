import inspect
import argparse

from keystoneclient.exceptions import HttpError

from contrail_api_cli import utils
from contrail_api_cli.utils import ShellContext
from contrail_api_cli import client

from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter


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


class RelativeResourceEncoder(utils.ResourceEncoder):

    def default(self, obj):
        if isinstance(obj, utils.Path):
            return str(obj.relative_to(ShellContext.current_path))
        return super(RelativeResourceEncoder, self).default(obj)


class BaseCommand(object):
    description = ""

    def __init__(self):
        self.parser = ArgumentParser(prog=self.name,
                                     description=self.description)
        self.add_arguments_to_parser(self.parser)

    @utils.classproperty
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
                return utils.Resource(path.base, fq_name=path.name, fetch=True)
            except ValueError as e:
                return str(e)
        else:
            if path.is_collection or path.is_root:
                return "\n".join([str(i.path.relative_to(ShellContext.current_path))
                                  for i in utils.Collection(path.base, fetch=True)])
            elif path.is_resource:
                res = utils.Resource(path.base, uuid=path.name, fetch=True)
                json_data = client.to_json(res.data, cls=RelativeResourceEncoder)
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
            return len(utils.Collection(path.base))


@experimental
class Rm(Command):
    description = "Delete a resource"
    resource = Arg(nargs="?", help="Resource path", default='')
    recursive = Arg("-r", "--recursive", dest="recursive",
                    action="store_true", default=False,
                    help="Recursive delete of back_refs resources")
    force = Arg("-f", "--force", dest="force",
                action="store_true", default=False,
                help="Don't ask for confirmation")

    def _get_back_refs(self, resource, back_refs):
        resource.fetch()
        if resource in back_refs:
            back_refs.remove(resource)
        back_refs.append(resource)
        for back_ref in resource.back_refs:
            back_refs = self._get_back_refs(back_ref, back_refs)
        return back_refs

    def __call__(self, resource='', recursive=False, force=False):
        path = ShellContext.current_path / resource
        if not path.is_resource:
            raise CommandError('"%s" is not a resource.' % path.relative_to(ShellContext.current_path))

        resource = utils.Resource(path.base, uuid=path.name)
        back_refs = [resource]
        if recursive:
            back_refs = self._get_back_refs(resource, [])
        if back_refs:
            message = """About to delete:
 - %s""" % "\n - ".join([str(res.path.relative_to(ShellContext.current_path))
                         for res in back_refs])
            if force or utils.continue_prompt(message=message):
                for res in reversed(back_refs):
                    print("Deleting %s" % str(res.path))
                    try:
                        res.delete()
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
    return utils.all_subclasses(Command)


def shell_commands_list():
    return utils.all_subclasses(ShellCommand)


ls = ll = Ls()
cd = Cd()
help = Help()
count = Count()
rm = Rm()
exit = Exit()
