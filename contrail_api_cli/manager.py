from __future__ import unicode_literals
from six import add_metaclass
import argparse

from reentry import manager
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
        self.commands = {}
        if load_default is True:
            self.load_namespace('contrail_api_cli.command')

    def load_namespace(self, ns):
        """Load commands from namespace.

        :param ns: namespace name
        :type ns: str
        """
        for ext in manager.iter_entry_points(group=ns):
            try:
                obj = ext.load()
                self.commands[ext.name] = obj(ext.name)
            except Exception as err:
                self._on_failure(self, ext, err)
                self.commands[ext.name] = None

    def unload_namespace(self, ns):
        for ext in manager.iter_entry_points(group=ns):
            del self.commands[ext.name]

    def _on_failure(self, mgr, entrypoint, exc):
        print('Cannot load command %s: %s' % (entrypoint.name,
                                              exc))

    @property
    def list(self):
        """Generator of command instances

        :rtype: (name, Command)
        """
        for name, cmd in self.commands.items():
            yield (name, cmd)

    def get(self, name):
        """Return command instance of loaded
        commands by name

        :param name: name of the command
        :type name: str
        """
        if name not in self.commands:
            raise CommandNotFound('Command %s not found. Type help for all commands' % name)
        return self.commands[name]

    def add(self, name, cmd):
        """Add command to manager

        :param name: name of the command
        :type name: str
        :param cmd: command instance
        :type cmd: Command
        """
        self.commands[name] = cmd

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
