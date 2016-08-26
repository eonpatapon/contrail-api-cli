# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from stevedore import extension

from .context import Context
from .parser import CommandParser, CommandInvalid
from .exceptions import CommandNotFound
from .utils import printo


logger = logging.getLogger(__name__)


class ShellCompleter(Completer):

    def __init__(self):
        self.context = Context().shell
        self.completers = {}
        for ext in extension.ExtensionManager(namespace="contrail_api_cli.completer",
                                              invoke_on_load=True,
                                              on_load_failure_callback=self._on_failure):
            self.completers[ext.name] = ext.obj

    def _on_failure(self, mgr, entrypoint, exc):
        printo('Cannot load completer %s: %s' % (entrypoint.name,
                                                 exc))

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        words = document.text_before_cursor.split()
        try:
            self.parser = CommandParser(document)
        except CommandNotFound:
            if 'commands' in self.completers:
                for c in self.completers['commands'].get_completions(word_before_cursor, self.context):
                    yield c
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
            completer_name = arg.complete.split(':')[0]
            if completer_name in self.completers:
                for c in self.completers[completer_name].get_completions(word_before_cursor, self.context, arg):
                    yield c
            else:
                logger.warning('No completer found for %s' % completer_name)
            raise StopIteration

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
            completer_name = option.complete.split(':')[0]
            if completer_name in self.completers:
                for c in self.completers[completer_name].get_completions(word_before_cursor, self.context, option):
                    yield c
            else:
                logger.warning('No completer found for %s' % completer_name)

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
