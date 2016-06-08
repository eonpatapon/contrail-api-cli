# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type
import logging

from prompt_toolkit.completion import Completion

from .manager import CommandManager
from .exceptions import CommandNotFound, CommandInvalid
from .utils import Path


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

    def get_resource_completion(self, cache, current_path, text_before_cursor, option):
        cache_type, type, attr = option.complete.split(':')

        if attr == 'path':
            path = current_path / text_before_cursor
            if type and path.base != type:
                raise StopIteration
        else:
            path = Path('/')
            if type:
                path = path / type
            path = path / text_before_cursor

        logger.debug('Search for %s' % path)
        results = getattr(cache, 'search_' + cache_type)([text_type(path)])
        seen = set()
        for r in results:
            if (r.type, r.uuid) in seen:
                continue
            seen.add((r.type, r.uuid))
            if attr == 'path':
                value = text_type(r.path.relative_to(current_path))
            else:
                value = text_type(getattr(r, attr))
            if attr == 'fq_name':
                meta = r.uuid
            else:
                meta = text_type(r.fq_name)
            if value:
                yield Completion(value,
                                 -len(text_before_cursor),
                                 display_meta=meta)

    def get_option_name_completion(self, text_before_cursor):
        logger.debug('Complete option names')
        for option in self.available_options:
            option_name = option.short_name or option.long_name
            if text_before_cursor.startswith('--'):
                option_name = option.long_name
            if option_name.startswith(text_before_cursor):
                yield Completion(option_name,
                                 -len(text_before_cursor),
                                 display_meta=option.help)

    def get_option_value_completion(self, option, text_before_cursor, current_path, cache):
        logger.debug('Complete option value')
        # complete choices
        if option.kwargs.get('choices'):
            logger.debug('Complete using choices %s' % option.kwargs['choices'])
            for choice in option.kwargs['choices']:
                yield Completion(choice,
                                 -len(text_before_cursor))
        # complete resources
        elif option.complete is not None:
            logger.debug('Complete using option matcher %s' % option.complete)
            for c in self.get_resource_completion(cache, current_path,
                                                  text_before_cursor, option):
                yield c

    def get_last_option(self, text_before_cursor, words):
        # current option value
        if text_before_cursor:
            try:
                option = self.get_option(words[-2])
            except IndexError:
                option = None
        # no value typed
        else:
            option = self.get_option(words[-1])
        return option

    def get_last_arg(self, text_before_cursor, words):
        # current arg value
        if text_before_cursor:
            arg = list(self.used_args)[-1]
        # get the next arg in line
        else:
            arg = self.available_args.next()
        return arg

    def get_completions(self, cache, document, current_path):
        text_before_cursor = document.get_word_before_cursor(WORD=True)
        last_word = document.text_before_cursor[
            document.find_start_of_previous_word(WORD=True):].strip()
        words = document.text.split()

        logger.debug('text_before_cursor: %s' % text_before_cursor)
        logger.debug('last_word: %s' % last_word)

        # still typing the command
        if text_before_cursor == self.cmd_name:
            raise StopIteration

        # complete options for the current command
        if text_before_cursor.startswith('-'):
            for c in self.get_option_name_completion(text_before_cursor):
                yield c
            raise StopIteration

        # check we need a value for an option
        option = self.get_last_option(text_before_cursor, words)
        if option is not None and option.need_value:
            for c in self.get_option_value_completion(option, text_before_cursor,
                                                      current_path, cache):
                yield c
            raise StopIteration

        # check we need arguments values
        arg = self.get_last_arg(text_before_cursor, words)
        if arg is not None and arg.complete is not None:
            logger.debug('Complete using arg matcher %s' % arg.complete)
            for c in self.get_resource_completion(cache, current_path,
                                                  text_before_cursor, arg):
                yield c
            raise StopIteration
