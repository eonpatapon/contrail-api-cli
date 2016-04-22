from argparse import _AppendAction, _AppendConstAction

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

    def _get_action(self, option_str):
        for action in self.cmd.parser._actions:
            if option_str in action.option_strings:
                return action

    @property
    def options(self):
        """Return argparse optional actions

        rtype: argparse.Action generator
        """
        for action in self.cmd.parser._actions:
            if action.option_strings:
                yield action

    @property
    def used_options(self):
        """Return argparse optional actions already
        used in the command line

        rtype: argparse.Action generator
        """
        for option_str in filter(lambda c: c.startswith('-'), self.cmd_line):
            action = self._get_action(option_str)
            if action is not None:
                yield action

    @property
    def available_options(self):
        """Return argparse optional actions
        that can be used given the current cmd line

        rtype: argparse.Action generator
        """
        multiple_allowed = (_AppendAction, _AppendConstAction)
        for action in self.options:
            if (action not in list(self.used_options) or
                    any([isinstance(action, c) for c in multiple_allowed])):
                yield action

    # def _action_need_value(self, action):
        # classes = [_AppendAction, _AppendConstAction, _StoreAction]
        # return any([isinstance(action, cls) for cls in classes])

    # @property
    # def used_args(self):
        # values = []
        # for index, c in enumerate(self.cmd_line):
            # if index == 0:
                # continue
            # action = self._get_action(c)
            # prev_action = self._get_action(self.cmd_line[index - 1])
            # if action is None and self._action_need_value(prev_action):
                # continue
            # elif action is None:
                # values.append(c)
            # else:
                # continue
        # return list(self.args)

    # @property
    # def args(self):
        # for action in self.cmd.parser._actions:
            # if action.option_strings == []:
                # yield action
