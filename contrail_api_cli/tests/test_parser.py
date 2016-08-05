from __future__ import unicode_literals
import unittest

from prompt_toolkit.document import Document

from contrail_api_cli.command import Command, Arg, Option
from contrail_api_cli.manager import CommandManager
from contrail_api_cli.parser import CommandParser
from contrail_api_cli.exceptions import CommandNotFound, CommandInvalid

BASE = 'http://localhost:8082'


class TestCmd(Command):
    long = Option('-l', action="store_true")
    foo = Option(help="foo")
    bar = Option(nargs="*")
    arg1 = Arg(help="%(default)s", default="bar")
    arg2 = Arg()

    def __call__(self, *args, **kwargs):
        pass


class TestCmd2(Command):
    long = Option('-l', action="store_true")
    arg1 = Arg(help="%(default)s", default="bar")
    arg2 = Arg(nargs="*")

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
        self.assertEqual(self.cmd.args['arg1'].help, 'bar')

    def test_option_need_value(self):
        self.assertTrue(self.cmd.options['foo'].need_value)
        self.assertFalse(self.cmd.options['long'].need_value)

    def test_option_strings(self):
        self.assertEqual(['--long', '-l'], self.cmd.options['long'].option_strings)
        self.assertEqual(['--bar'], self.cmd.options['bar'].option_strings)

    def test_cmd_options(self):
        self.assertEqual(['long', 'foo', 'bar'], list(self.cmd.options.keys()))

    def test_cmd_args(self):
        self.assertEqual(['arg1', 'arg2'], list(self.cmd.args.keys()))


class TestParser(unittest.TestCase):

    def setUp(self):
        self.mgr = CommandManager()
        self.cmd = TestCmd('test-cmd')
        self.cmd2 = TestCmd2('test-cmd2')
        self.mgr.add('test-cmd', self.cmd)
        self.mgr.add('test-cmd2', self.cmd2)

    def test_bad_cmd(self):
        with self.assertRaises(CommandInvalid):
            CommandParser(Document('foo -h'))
        with self.assertRaises(CommandInvalid):
            CommandParser(Document('bar '))
        with self.assertRaises(CommandNotFound):
            CommandParser(Document())
        with self.assertRaises(CommandNotFound):
            CommandParser(Document('ex'))

    def test_cmd(self):
        parser = CommandParser(Document('test-cmd'))
        self.assertEqual(parser.cmd, self.mgr.get('test-cmd'))
        self.assertEqual(parser.cmd_name, 'test-cmd')

    def test_option_parsing(self):
        parser = CommandParser(Document('test-cmd -h'))
        self.assertEqual(len(list(parser.used_options)), 0)
        expected = ['-l', '--foo', '--bar']
        parsed = [o.short_name or o.long_name for o in parser.available_options]
        self.assertEqual(parsed, expected)

        parser = CommandParser(Document('test-cmd --bar -h'))
        self.assertEqual(len(list(parser.used_options)), 1)
        expected = ['-l', '--foo', '--bar']
        parsed = [o.short_name or o.long_name for o in parser.available_options]
        self.assertEqual(parsed, expected)

    def test_arg_parsing(self):
        parser = CommandParser(Document('test-cmd --foo bar arg1_value -l arg2_value '))
        self.assertEqual(list(parser.used_args), [self.cmd.args['arg1'], self.cmd.args['arg2']])
        parser = CommandParser(Document('test-cmd arg1_value -l'))
        self.assertEqual(list(parser.used_args), [self.cmd.args['arg1']])
        self.assertEqual(list(parser.available_args), [self.cmd.args['arg2']])

        parser = CommandParser(Document('test-cmd2 arg1_value -l'))
        self.assertEqual(list(parser.available_args), [self.cmd2.args['arg2']])
        parser = CommandParser(Document('test-cmd2 arg1_value -l arg2_value'))
        self.assertEqual(list(parser.available_args), [self.cmd2.args['arg2']])
        parser = CommandParser(Document('test-cmd2 arg1_value -l arg2_value arg2_value2'))
        self.assertEqual(list(parser.available_args), [self.cmd2.args['arg2']])


if __name__ == "__main__":
    unittest.main()
