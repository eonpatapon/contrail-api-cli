import inspect
import argparse
import json

from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter

from contrail_api_cli import utils
from contrail_api_cli.client import APIClient


class CommandError(Exception):
    pass


class ArgumentParser(argparse.ArgumentParser):

    def exit(self, status=0, message=None):
        print(message)
        raise CommandError()


class Arg:

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class Command:
    description = ""

    def __init__(self, *args):
        self.parser = ArgumentParser(prog=self.__class__.__name__.lower(),
                                     description=self.description)
        for attr, value in inspect.getmembers(self.__class__):
            if isinstance(value, Arg):
                self.parser.add_argument(attr, *value.args, **value.kwargs)

    def __call__(self, path, *args):
        args = self.parser.parse_args(args=args)
        return self.run(path, **args.__dict__)


class Ls(Command):
    description = "List resource objects"
    resource = Arg(nargs="?", help="Resource path")

    def walk_resource(self, data, current_path):
        data = self.transform_resource(data, current_path)
        for attr, value in list(data.items()):
            if attr.endswith('refs'):
                for idx, r in enumerate(data[attr]):
                    data[attr][idx] = self.walk_resource(data[attr][idx], current_path)
            if type(data[attr]) is dict:
                data[attr] = self.walk_resource(data[attr], current_path)
        return data

    def transform_resource(self, data, current_path):
        for attr, value in list(data.items()):
            if value is None:
                del data[attr]
            if attr in ("to", "fq_name"):
                data[attr] = ":".join(value)
            if attr in ("href", "parent_href"):
                data[attr] = value.relative(current_path)
                utils.COMPLETION_QUEUE.put(value)
        return data

    def colorize(self, data):
        json_data = json.dumps(data, sort_keys=True, indent=2,
                               cls=utils.PathEncoder,
                               separators=(',', ': '))
        return highlight(json_data,
                         JsonLexer(indent=2),
                         Terminal256Formatter(bg="dark"))

    def run(self, path, resource=None):
        target = utils.Path(str(path), resource)
        data = APIClient().list(target)
        if target.is_resource:
            data = self.walk_resource(data, path)
            return self.colorize(data)
        else:
            return data


class Count(Command):
    description = "Count number of resources"
    resource = Arg(nargs="?", help="Resource path")

    def run(self, path, resource=None):
        target = utils.Path(str(path), resource)
        if target.resource_name and not target.is_resource:
            data = APIClient().request(target, count=True)
            return data[target.resource_name + "s"]["count"]


class Cd(Command):
    description = "Change resource context"
    resource = Arg(nargs="?", help="Resource path")

    def run(self, path, resource=None):
        path.cd(resource)


class Help(Command):

    def run(self, path):
        return "You are so lost buddy."


ls = ll = Ls()
cd = Cd()
help = Help()
count = Count()
