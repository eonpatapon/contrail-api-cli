# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type

from prompt_toolkit.completion import Completion

from .manager import CommandManager
from .exceptions import CommandNotFound, CommandInvalid


class NoCompletions(Exception):
    pass


class CommandParser(object):

    def __init__(self, cmd_line):
        self.mgr = CommandManager()

        self.cmd_line_text = cmd_line
        self.cmd_line = list(filter(lambda i: len(i) > 1, cmd_line.split()))

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

    def search_completions(self, cache, current_path, text_before_cursor, option):
        cache_type, type, attr = option.complete.split(':')
        path = current_path / text_before_cursor
        if type and attr is 'path':
            type_path = current_path / type
            if not (text_type(path).startswith(text_type(type_path)) or
                    text_type(type_path).startswith(text_type(path))):
                raise StopIteration
        results = getattr(cache, 'search_' + cache_type)([text_type(path)])
        for r in results:
            if attr == 'path':
                value = text_type(r.path.relative_to(current_path))
            else:
                value = text_type(getattr(r, attr))
            if value:
                yield Completion(value,
                                 -len(text_before_cursor),
                                 display_meta=text_type(r.fq_name))

    def get_completions(self, cache, document, current_path):
        text_before_cursor = document.get_word_before_cursor(WORD=True)
        last_word = document.text_before_cursor[
            document.find_start_of_previous_word(WORD=True):].strip()

        # complete options for the current command
        if text_before_cursor.startswith('-'):
            for option in self.available_options:
                option_name = option.short_name or option.long_name
                if text_before_cursor.startswith('--'):
                    option_name = option.long_name
                if option_name.startswith(text_before_cursor):
                    yield Completion(option_name,
                                     -len(text_before_cursor),
                                     display_meta=option.help)
            raise StopIteration

        option = self.get_option(last_word)
        if option is not None:
            # complete choices
            for choice in option.kwargs.get('choices', []):
                yield Completion(choice,
                                 -len(text_before_cursor))
            # complete resources
            if option.complete:
                for c in self.search_completions(cache, current_path,
                                                 text_before_cursor, option):
                    yield c

        else:
            arg = self.available_args.next()
            if arg and arg.complete:
                for c in self.search_completions(cache, current_path,
                                                 text_before_cursor, arg):
                    yield c

        raise StopIteration
