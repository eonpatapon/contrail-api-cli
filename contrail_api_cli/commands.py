import inspect
import argparse

from keystoneclient.exceptions import HttpError

from contrail_api_cli import utils
from contrail_api_cli.utils import ShellContext
from contrail_api_cli.client import APIClient


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

    def __call__(self, resource=''):
        # Find Path from fq_name
        if ":" in resource:
            target = APIClient().fqname_to_id(ShellContext.current_path, resource)
            if target is None:
                print("Can't find %s" % resource)
                return
        else:
            target = ShellContext.current_path / resource

        if target.is_collection or target.is_root:
            return utils.Collection(path=target)
        elif target.is_resource:
            return utils.Resource(path=target)


class Count(Command):
    description = "Count number of resources"
    resource = Arg(nargs="?", help="Resource path", default='')

    def __call__(self, resource=''):
        target = ShellContext.current_path / resource
        if target.is_collection:
            data = APIClient().get(target, count=True)
            return data[target.resource_name + "s"]["count"]


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

    def _get_back_refs(self, path, back_refs):
        resource = APIClient().get(path)[path.resource_name]
        if resource["href"] in back_refs:
            back_refs.remove(resource["href"])
        back_refs.append(resource["href"])
        for attr, values in resource.items():
            if not attr.endswith(("back_refs", "loadbalancer_members")):
                continue
            for back_ref in values:
                back_refs = self._get_back_refs(back_ref["href"],
                                                back_refs)
        return back_refs

    def __call__(self, resource='', recursive=False, force=False):
        target = ShellContext.current_path / resource
        if not target.is_resource:
            raise CommandError('"%s" is not a resource.' % target.relative_to(ShellContext.current_path))

        back_refs = [target]
        if recursive:
            back_refs = self._get_back_refs(target, [])
        if back_refs:
            message = """About to delete:
 - %s""" % "\n - ".join([str(p.relative_to(ShellContext.current_path)) for p in back_refs])
            if force or utils.continue_prompt(message=message):
                for ref in reversed(back_refs):
                    print("Deleting %s" % str(ref))
                    try:
                        APIClient().delete(ref)
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
