from .manager import CommandManager
from .exceptions import CommandNotFound, CommandInvalid


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
