# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from .manager import CommandManager
from .exceptions import CommandNotFound, CommandInvalid


logger = logging.getLogger(__name__)


class NoCompletions(Exception):
    pass


class CommandParser(object):

    def __init__(self, cmd_line):
        logger.debug("Init parser with %s" % cmd_line)
        self.mgr = CommandManager()

        self.cmd_line_text = cmd_line
        self.cmd_line = cmd_line.split()

        try:
            self.cmd_name = self.cmd_line[0]
            self.cmd = self.mgr.get(self.cmd_name)
        except IndexError:
            # no command in string
            raise CommandNotFound
        except CommandNotFound:
            # partial command
            if self.cmd_name == self.cmd_line_text:
                raise
            # invalid command in string
            else:
                raise CommandInvalid

    @property
    def used_options(self):
        """Return options already used in the
        command line

        rtype: command.Option generator
        """
        for option_str in filter(lambda c: c.startswith('-'), self.cmd_line):
            for option in list(self.cmd.options.values()):
                if option_str in option.option_strings:
                    yield option

    @property
    def available_options(self):
        """Return options that can be used given
        the current cmd line

        rtype: command.Option generator
        """
        for option in list(self.cmd.options.values()):
            if (option.is_multiple or
                    option not in list(self.used_options)):
                yield option

    @property
    def used_args(self):
        """Return args already used in the
        command line

        rtype: command.Arg generator
        """
        # get all arguments values from the command line
        values = []
        for idx, c in enumerate(self.cmd_line[1:]):
            if c.startswith('-'):
                continue
            option_str = self.cmd_line[1:][idx - 1]
            option = self.get_option(option_str)
            if option is None or not option.need_value:
                values.append(c)
        # consume values
        for arg in self.cmd.args.values():
            if not values:
                raise StopIteration
            if arg.is_multiple:
                values = []
            else:
                values = values[1:]
            yield arg

    @property
    def available_args(self):
        """Return args that can be used given
        the current cmd line

        rtype: command.Arg generator
        """
        for arg in list(self.cmd.args.values()):
            if (arg.is_multiple or
                    arg not in list(self.used_args)):
                yield arg

    def get_option(self, option_str):
        for option in self.used_options:
            if option_str in option.option_strings:
                return option
