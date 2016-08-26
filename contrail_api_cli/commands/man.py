# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg
from ..manager import CommandManager
from ..utils import printo
from ..exceptions import CommandError

try:
    from rst2ansi import rst2ansi
except ImportError:
    def rst2ansi(s):
        return s.decode('utf-8')


class Man(Command):
    """Show command documentation.

    To improve the output you can install the rst2ansi package.
    """
    description = "Show command help"
    cmd_name = Arg(help="Command name", complete="commands")

    def __call__(self, cmd_name=None):
        cmd = CommandManager().get(cmd_name)
        if cmd.__doc__ is not None:
            printo(rst2ansi(cmd.__doc__.encode('utf-8')) + "\n")
        else:
            raise CommandError("No doc available for this command")
