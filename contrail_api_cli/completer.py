# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from six import text_type

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from .context import Context
from .resource import ResourceCache
from .manager import CommandManager
from .parser import CommandParser, CommandInvalid
from .exceptions import CommandNotFound
from .utils import Path


logger = logging.getLogger(__name__)


class ShellCompleter(Completer):

    def __init__(self):
        self.manager = CommandManager()
        self.cache = ResourceCache()
        self.context = Context().shell

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        words = document.text_before_cursor.split()
        try:
            self.parser = CommandParser(document)
        except CommandNotFound:
            for cmd_name, cmd in self.manager.list:
                if cmd_name.startswith(word_before_cursor):
                    yield Completion(cmd_name,
                                     -len(word_before_cursor),
                                     display_meta=cmd.description)
            raise StopIteration
        except CommandInvalid:
            raise StopIteration

        # still typing the command
        if word_before_cursor == self.parser.cmd_name:
            raise StopIteration

        # complete options for the current command
        if word_before_cursor.startswith('-'):
            for c in self.get_option_name_completion(word_before_cursor):
                yield c
            raise StopIteration

        # check we need a value for an option
        option = self.get_last_option(word_before_cursor, words)
        if option is not None and option.need_value:
            for c in self.get_option_value_completion(option, word_before_cursor):
                yield c
            raise StopIteration

        # check we need arguments values
        arg = self.get_last_arg(word_before_cursor, words)
        if arg is not None and arg.complete is not None:
            logger.debug('Complete using arg matcher %s' % arg.complete)
            for c in self.get_resource_completion(word_before_cursor, arg):
                yield c
            raise StopIteration

    def get_resource_completion(self, word_before_cursor, option):
        cache_type, type, attr = option.complete.split(':')

        if attr == 'path':
            path = self.context.current_path / word_before_cursor
            if type and path.base != type:
                raise StopIteration
        else:
            path = Path('/')
            if type:
                path = path / type
            path = path / word_before_cursor

        logger.debug('Search for %s' % path)
        results = getattr(self.cache, 'search_' + cache_type)([text_type(path)])
        seen = set()
        for r in results:
            if (r.type, r.uuid) in seen:
                continue
            seen.add((r.type, r.uuid))
            if attr == 'path':
                value = text_type(r.path.relative_to(self.context.current_path))
            else:
                value = text_type(getattr(r, attr))
            if attr == 'fq_name':
                meta = r.uuid
            else:
                meta = text_type(r.fq_name)
            if value:
                yield Completion(value,
                                 -len(word_before_cursor),
                                 display_meta=meta)

    def get_option_name_completion(self, word_before_cursor):
        logger.debug('Complete option names')
        for option in self.parser.available_options:
            option_name = option.short_name or option.long_name
            if word_before_cursor.startswith('--'):
                option_name = option.long_name
            if option_name.startswith(word_before_cursor):
                yield Completion(option_name,
                                 -len(word_before_cursor),
                                 display_meta=option.help)

    def get_option_value_completion(self, option, word_before_cursor):
        logger.debug('Complete option value')
        # complete choices
        if option.kwargs.get('choices'):
            logger.debug('Complete using choices %s' % option.kwargs['choices'])
            for choice in option.kwargs['choices']:
                yield Completion(choice,
                                 -len(word_before_cursor))
        # complete resources
        elif option.complete is not None:
            logger.debug('Complete using option matcher %s' % option.complete)
            for c in self.get_resource_completion(word_before_cursor, option):
                yield c

    def get_last_option(self, word_before_cursor, words):
        # current option value
        if word_before_cursor:
            try:
                option = self.parser.get_option(words[-2])
            except IndexError:
                option = None
        # no value typed
        else:
            option = self.parser.get_option(words[-1])
        return option

    def get_last_arg(self, word_before_cursor, words):
        # current arg value
        if word_before_cursor and list(self.parser.available_args):
            # depending on the cursor position, use a relative
            # parser to get the current argument
            p = CommandParser(Document(text=" ".join(words)))
            arg = list(p.available_args)[0]
        # get the next arg in line
        else:
            arg = next(self.parser.available_args)
        return arg
