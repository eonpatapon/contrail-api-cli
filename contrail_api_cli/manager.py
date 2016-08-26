from __future__ import unicode_literals
from six import add_metaclass
import itertools
import argparse

from stevedore import extension
from prompt_toolkit.completion import Completion

from .exceptions import CommandNotFound
from .utils import Singleton


@add_metaclass(Singleton)
class CommandManager(object):

    def __init__(self, load_default=True):
        """Load commands from namespace

        :param load_default: tell the manager to load the default
                             namespace for commands (contrail_api_cli.command).
                             (True by default)
        :type load_default: bool
        """
        self.mgrs = []
        if load_default is True:
            self.load_namespace('contrail_api_cli.command')

    def load_namespace(self, ns):
        """Load commands from namespace.

        :param ns: namespace name
        :type ns: str
        """
        mgr = extension.ExtensionManager(namespace=ns,
                                         verify_requirements=True,
                                         on_load_failure_callback=self._on_failure)
        # Load commands from ns
        for ext in mgr.extensions:
            try:
                obj = ext.plugin(ext.name)
            except Exception as err:
                self._on_failure(self, ext, err)
                obj = None
            ext.obj = obj

        self.mgrs.append(mgr)

    def unload_namespace(self, ns):
        self.mgrs = [mgr for mgr in self.mgrs if not mgr.namespace == ns]

    def _on_failure(self, mgr, entrypoint, exc):
        print('Cannot load command %s: %s' % (entrypoint.name,
                                              exc))

    def get(self, name):
        """Return command instance of loaded
        commands by name

        :param name: name of the command
        :type name: str
        """
        for cmd_name, cmd in self.list:
            if cmd_name == name:
                return cmd
        raise CommandNotFound('Command %s not found. Type help for all commands' % name)

    @property
    def extensions(self):
        return itertools.chain(*[mgr.extensions for mgr in self.mgrs])

    @property
    def list(self):
        """Generator of command instances

        :rtype: (name, Command)
        """
        for ext in self.extensions:
            # don't return ext that failed
            # to load earlier
            if ext.obj is None:
                continue
            yield (ext.name, ext.obj)

    def add(self, name, cmd):
        ext = extension.Extension(name, None, cmd.__class__, cmd)
        self.mgrs[0].extensions.append(ext)

    @classmethod
    def register_argparse_commands(cls, parser, argv):
        in_parser = argparse.ArgumentParser(add_help=False)
        for p in (parser, in_parser):
            p.add_argument('--ns',
                           help='Command namespaces to load (default: %(default)s)',
                           metavar='COMMAND_NAMESPACE',
                           action='append',
                           default=[])
        options, _ = in_parser.parse_known_args(argv)
        mgr = CommandManager()
        for ns in options.ns:
            mgr.load_namespace(ns)
        subparsers = parser.add_subparsers(dest='subcmd')
        for cmd_name, cmd in mgr.list:
            subparser = subparsers.add_parser(cmd_name, help=cmd.description)
            cmd.add_arguments_to_parser(subparser)
        return mgr

    def get_completions(self, word_before_cursor, context, option=None):
        for cmd_name, cmd in self.list:
            if cmd_name.startswith(word_before_cursor):
                yield Completion(cmd_name,
                                 -len(word_before_cursor),
                                 display_meta=cmd.description)
