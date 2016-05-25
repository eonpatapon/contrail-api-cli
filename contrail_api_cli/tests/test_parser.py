from __future__ import unicode_literals
import unittest

from contrail_api_cli.command import Command, Arg, Option
from contrail_api_cli.manager import CommandManager
from contrail_api_cli.parser import CommandParser
from contrail_api_cli.exceptions import CommandNotFound, CommandInvalid

BASE = 'http://localhost:8082'


class TestCmd(Command):
    paths = Arg(help="%(default)s", default="bar")
    long = Option('-l', action="store_true")
    foo = Option(help="foo")
    bar = Option(nargs="*")

    def __call__(self, *args, **kwargs):
        pass


class TestCommandOptions(unittest.TestCase):

    def setUp(self):
        self.cmd = TestCmd('test-cmd')

    def test_option_multiple(self):
        self.assertTrue(self.cmd.options['bar'].is_multiple)
        self.assertFalse(self.cmd.options['foo'].is_multiple)

    def test_option_help(self):
        self.assertEqual(self.cmd.options['foo'].help, 'foo')
        self.assertEqual(self.cmd.options['bar'].help, '')
        self.assertEqual(self.cmd.args['paths'].help, 'bar')

    def test_option_strings(self):
        self.assertEqual(['--long', '-l'], self.cmd.options['long'].option_strings)
        self.assertEqual(['--bar'], self.cmd.options['bar'].option_strings)

    def test_cmd_options(self):
        self.assertEqual(['bar', 'foo', 'long'], list(self.cmd.options.keys()))

    def test_cmd_args(self):
        self.assertEqual(['paths'], list(self.cmd.args.keys()))


class TestParser(unittest.TestCase):

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
        self.assertEqual(len(list(parser.used_options)), 0)
        expected = ['--bar', '--foo', '-l']
        parsed = [o.short_name or o.long_name for o in parser.available_options]
        self.assertEqual(parsed, expected)

        parser = CommandParser('test-cmd --bar -h')
        self.assertEqual(len(list(parser.used_options)), 1)
        expected = ['--bar', '--foo', '-l']
        parsed = [o.short_name or o.long_name for o in parser.available_options]
        self.assertEqual(parsed, expected)

    # def test_arg_parsing(self):
        # parser = CommandParser('test-cmd --foo bar -l res1')
        # self.assertEqual(list(parser.used_args), [('args', 'res1')])


if __name__ == "__main__":
    unittest.main()
