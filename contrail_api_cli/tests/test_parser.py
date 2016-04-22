from __future__ import unicode_literals
import unittest

from contrail_api_cli.command import Command, Arg
from contrail_api_cli.manager import CommandManager
from contrail_api_cli.parser import CommandParser
from contrail_api_cli.exceptions import CommandNotFound, CommandInvalid

BASE = 'http://localhost:8082'


class TestCmd(Command):
    args = Arg(help="Resources")
    long_format = Arg('-l', action="store_true")
    foo = Arg('--foo', help="foo")
    bar = Arg('--bar', nargs="*")

    def __call__(self, *args, **kwargs):
        pass


class TestCompletion(unittest.TestCase):

    def setUp(self):
        self.mgr = CommandManager()
        self.cmd = TestCmd('test-cmd')
        self.mgr.add('test-cmd', self.cmd)

    def test_bad_cmd(self):
        with self.assertRaises(CommandInvalid):
            CommandParser('foo -h')
        with self.assertRaises(CommandInvalid):
            CommandParser('bar ')
        with self.assertRaises(CommandNotFound):
            CommandParser('')
        with self.assertRaises(CommandNotFound):
            CommandParser('ex')

    def test_cmd(self):
        parser = CommandParser('test-cmd')
        self.assertEqual(parser.cmd, self.mgr.get('test-cmd'))
        self.assertEqual(parser.cmd_name, 'test-cmd')

    def test_option_parsing(self):
        parser = CommandParser('test-cmd -h')
        self.assertEqual(len(list(parser.used_options)), 1)
        expected = ['--bar', '--foo', '-l']
        parsed = [a.option_strings[0] for a in parser.available_options]
        self.assertEqual(parsed, expected)

        parser = CommandParser('test-cmd --foo -h')
        self.assertEqual(len(list(parser.used_options)), 2)
        expected = ['--bar', '-l']
        parsed = [a.option_strings[0] for a in parser.available_options]
        self.assertEqual(parsed, expected)

    # def test_arg_parsing(self):
        # parser = CommandParser('test-cmd --foo bar -l res1')
        # self.assertEqual(list(parser.used_args), [('args', 'res1')])


if __name__ == "__main__":
    unittest.main()
