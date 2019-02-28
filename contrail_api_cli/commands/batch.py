# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import shlex
import fileinput

from ..command import Command, Arg
from ..manager import CommandManager
from ..exceptions import CommandError, CommandNotFound
from ..utils import printo


class Batch(Command):
    """Execute commands from file(s) for batch processing
    The `batch` command can be used to execute several
    `contrail-api-cli` commands read from file(s) or from
    stdin.

    This command works like normal shell commands, it accepts
    a list of files as argument, and it will execute the
    commands read from those files one by one. If no filename
    is provided (or filename is `-`), it reads commands from
    standard input.

    The file(s) are read line by line, empty lines or lines
    beginning with `#` are skipped. Each line has to be a
    proper `contrail-api-cli` command line.

    In case of any error, batch execution is stopped to
    avoid unwanted behaviour.
    """
    description = "Run commands from a batch file(s)/stdin"
    files = Arg(nargs="*", help="List of files")

    def __call__(self, files=None):
        manager = CommandManager()
        try:
            for line in fileinput.input(files=files):
                if line[0] == '#':
                    continue
                action = shlex.split(line.rstrip())
                if len(action) < 1:
                    continue
                cmd = manager.get(action[0])
                args = action[1:]
                result = cmd.parse_and_call(*args)
                if result:
                    printo(result)
        except IOError:
            raise CommandError("Cannot read from file: {}".format(fileinput.filename()))
        except CommandNotFound:
            raise CommandError("Command {} not found".format(action[0]))
        finally:
            fileinput.close()
