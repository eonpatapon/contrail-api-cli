# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import argparse

from ..command import Command, Arg


class Exec(Command):
    description = "Run a python script inside the cli"
    script = Arg(help="script path to run",
                 type=argparse.FileType('r'))

    def __call__(self, script=None):
        exec(script)
