
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from .resource import ResourceCache
from .parser import CommandParser, CommandInvalid
from .exceptions import CommandNotFound


class ShellCompleter(Completer):

    def __init__(self, aliases, shell_context, manager):
        self.mgr = manager
        self.cache = ResourceCache()
        self.aliases = aliases
        self.context = shell_context

    def get_completions(self, document, complete_event):
        text_before_cursor = document.get_word_before_cursor(WORD=True)
        text = self.aliases.apply(document.text)
        try:
            parser = CommandParser(text)
            for c in parser.get_completions(self.cache, Document(text=text),
                                            self.context.current_path):
                yield c
        except CommandNotFound:
            for cmd_name, cmd in self.mgr.list:
                if cmd_name.startswith(text_before_cursor):
                    yield Completion(cmd_name,
                                     -len(text_before_cursor),
                                     display_meta=cmd.description)
            raise StopIteration
        except CommandInvalid:
            raise StopIteration
