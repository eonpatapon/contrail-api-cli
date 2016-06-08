# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from six import text_type

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from .resource import ResourceCache
from .parser import CommandParser, CommandInvalid
from .exceptions import CommandNotFound
from .utils import Path


logger = logging.getLogger(__name__)


class ShellCompleter(Completer):

    def __init__(self, aliases, shell_context, manager):
        self.mgr = manager
        self.cache = ResourceCache()
        self.aliases = aliases
        self.context = shell_context

    def get_completions(self, document, complete_event):
        text = self.aliases.apply(document.text)
        doc = Document(text=text)
        text_before_cursor = doc.get_word_before_cursor(WORD=True)
        last_word = doc.text_before_cursor[
            document.find_start_of_previous_word(WORD=True):].strip()
        words = doc.text.split()
        try:
            self.parser = CommandParser(text)
        except CommandNotFound:
            for cmd_name, cmd in self.mgr.list:
                if cmd_name.startswith(text_before_cursor):
                    yield Completion(cmd_name,
                                     -len(text_before_cursor),
                                     display_meta=cmd.description)
            raise StopIteration
        except CommandInvalid:
            raise StopIteration

        logger.debug('text_before_cursor: %s' % text_before_cursor)
        logger.debug('last_word: %s' % last_word)

        # still typing the command
        if text_before_cursor == self.parser.cmd_name:
            raise StopIteration

        # complete options for the current command
        if text_before_cursor.startswith('-'):
            for c in self.get_option_name_completion(text_before_cursor):
                yield c
            raise StopIteration

        # check we need a value for an option
        option = self.get_last_option(text_before_cursor, words)
        if option is not None and option.need_value:
            for c in self.get_option_value_completion(option, text_before_cursor):
                yield c
            raise StopIteration

        # check we need arguments values
        arg = self.get_last_arg(text_before_cursor, words)
        if arg is not None and arg.complete is not None:
            logger.debug('Complete using arg matcher %s' % arg.complete)
            for c in self.get_resource_completion(text_before_cursor, arg):
                yield c
            raise StopIteration

    def get_resource_completion(self, text_before_cursor, option):
        cache_type, type, attr = option.complete.split(':')

        if attr == 'path':
            path = self.context.current_path / text_before_cursor
            if type and path.base != type:
                raise StopIteration
        else:
            path = Path('/')
            if type:
                path = path / type
            path = path / text_before_cursor

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
                                 -len(text_before_cursor),
                                 display_meta=meta)

    def get_option_name_completion(self, text_before_cursor):
        logger.debug('Complete option names')
        for option in self.parser.available_options:
            option_name = option.short_name or option.long_name
            if text_before_cursor.startswith('--'):
                option_name = option.long_name
            if option_name.startswith(text_before_cursor):
                yield Completion(option_name,
                                 -len(text_before_cursor),
                                 display_meta=option.help)

    def get_option_value_completion(self, option, text_before_cursor):
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
            for c in self.get_resource_completion(text_before_cursor, option):
                yield c

    def get_last_option(self, text_before_cursor, words):
        # current option value
        if text_before_cursor:
            try:
                option = self.parser.get_option(words[-2])
            except IndexError:
                option = None
        # no value typed
        else:
            option = self.parser.get_option(words[-1])
        return option

    def get_last_arg(self, text_before_cursor, words):
        # current arg value
        if text_before_cursor:
            arg = list(self.parser.used_args)[-1]
        # get the next arg in line
        else:
            arg = self.parser.available_args.next()
        return arg
