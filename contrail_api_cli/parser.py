# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from .manager import CommandManager
from .exceptions import CommandNotFound, CommandInvalid


logger = logging.getLogger(__name__)


class NoCompletions(Exception):
    pass


class CommandParser(object):

    def __init__(self, document):
        logger.debug("Init parser with %s" % document)

        self.mgr = CommandManager()
        self.document = document
        self.words = document.text.split()

        try:
            self.cmd_name = self.words[0]
            self.cmd = self.mgr.get(self.cmd_name)
        except IndexError:
            # no command in string
            raise CommandNotFound
        except CommandNotFound:
            # partial command
            if self.cmd_name == self.document.text_before_cursor:
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
        for option_str in filter(lambda c: c.startswith('-'), self.words):
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
        for idx, c in enumerate(self.words[1:]):
            if c.startswith('-'):
                continue
            option_str = self.words[1:][idx - 1]
            option = self.get_option(option_str)
            if option is None or not option.need_value:
                values.append((c, c == self.document.get_word_before_cursor(WORD=True)))
        logger.debug("Found args values %s" % values)
        # consume values
        for arg in self.cmd.args.values():
            if not values:
                raise StopIteration
            if arg.is_multiple:
                values = []
                yield arg
            elif type(arg.nargs) is int:
                for _ in range(arg.nargs):
                    value = values.pop(0)
                    # not the current argument
                    if value[1] is False:
                        yield arg
                    if not values:
                        raise StopIteration

    @property
    def available_args(self):
        """Return args that can be used given
        the current cmd line

        rtype: command.Arg generator
        """
        used = list(self.used_args)
        logger.debug('Found used args: %s' % used)
        for arg in list(self.cmd.args.values()):
            if (arg.is_multiple or
                    arg not in used):
                yield arg
            elif (type(arg.nargs) is int and
                    arg.nargs > 1 and
                    not arg.nargs == used.count(arg)):
                yield arg

    def get_option(self, option_str):
        for option in self.used_options:
            if option_str in option.option_strings:
                return option
