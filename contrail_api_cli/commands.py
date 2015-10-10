import inspect
import argparse
import json

from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter

from contrail_api_cli import utils
from contrail_api_cli.client import APIClient, BASE_URL


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

    def find_resources(self, data, current_path):
        if not type(data) == dict:
            return
        for attr, value in data.items():
            if attr in ("href", "parent_href"):
                path = utils.Path(value[len(BASE_URL):])
                if data.get('to'):
                    path.meta["fq_name"] = ":".join(data['to'])
                if data.get('fq_name'):
                    path.meta["fq_name"] = ":".join(data['fq_name'])
                data[attr] = str(path.relative(current_path))
                utils.COMPLETION_QUEUE.put(path)
            if type(value) == dict:
                self.find_resources(value, current_path)
            if type(value) == list:
                for r in value:
                    self.find_resources(r, current_path)

    def run(self, path, resource=None):
        target = utils.Path(str(path))
        if resource is not None:
            target.cd(resource)
        client = APIClient()
        data = client.list(target)
        if target.is_resource:
            self.find_resources(data, path)
            json_data = json.dumps(data, sort_keys=True, indent=2,
                                   separators=(',', ': '))
            return highlight(json_data,
                             JsonLexer(indent=2),
                             Terminal256Formatter(bg="dark"))
        else:
            return data


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
