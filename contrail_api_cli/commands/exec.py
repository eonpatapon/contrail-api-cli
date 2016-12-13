# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import argparse

from ..command import Command, Arg


class Exec(Command):
    """Run python script inside the cli context.

    The script content is executed using `exec` python
    builtin.

    All script arguments can be accessed from the args
    variable inside the script::

        contrail-api-cli exec test.py arg1 arg2

    Inside the script args will be ['arg1', 'arg2'].

    This method is used to write quick debugging scripts,
    if you need a complete handling of arguments or options
    consider to write a proper command.
    """
    description = "Run a python script inside the cli"
    script = Arg(help="script path to run",
                 type=argparse.FileType('r'))
    script_args = Arg(help="script args",
                      nargs="*")

    def __call__(self, script=None, script_args=None):
        exec(script, {'args': script_args})
