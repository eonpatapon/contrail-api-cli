from __future__ import unicode_literals
import unittest
try:
    import mock
except ImportError:
    import unittest.mock as mock

from keystoneauth1.exceptions.http import HttpError

from prompt_toolkit.document import Document

from contrail_api_cli.context import Context
from contrail_api_cli.completer import ShellCompleter
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import ResourceNotFound

from .utils import CLITest


class TestCompleter(CLITest):

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_add_del_resource(self, mock_session):
        mock_document = Document(text='cat bar')

        comp = ShellCompleter()
        r1 = Resource('foo', uuid='d8eb36b4-9c57-49c5-9eac-95bedc90eb9a')
        r2 = Resource('bar', uuid='4c6d3711-61f1-4505-b8df-189d32b52872')
        completions = comp.get_completions(mock_document, None)
        self.assertTrue(str(r2.path.relative_to(Context().shell.current_path)) in
                        [c.text for c in completions])

        r1.delete()
        r2.delete()
        completions = comp.get_completions(mock_document, None)
        self.assertTrue(str(r2.path.relative_to(Context().shell.current_path)) not in
                        [c.text for c in completions])

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_add_same_resource(self, mock_session):
        mock_document = Document(text='cat bar')

        comp = ShellCompleter()
        r1 = Resource('bar', uuid='4c6d3711-61f1-4505-b8df-189d32b52872')
        r2 = Resource('bar', uuid='4c6d3711-61f1-4505-b8df-189d32b52872')
        completions = comp.get_completions(mock_document, None)
        self.assertEqual(len(list(completions)), 1)
        r1.delete()
        completions = comp.get_completions(mock_document, None)
        self.assertEqual(len(list(completions)), 0)
        r2.delete()

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_cursor_position(self, mock_session):
        mock_document = Document(text='cat bar --foo bar', cursor_position=6)
        comp = ShellCompleter()
        Resource('bar', uuid='4c6d3711-61f1-4505-b8df-189d32b52872')
        Resource('foo', uuid='7413a49b-4f17-4340-b93f-7e03b29b5a9d')
        completions = comp.get_completions(mock_document, None)
        self.assertEqual(len(list(completions)), 1)

        mock_document = Document(text='ls -P  foo', cursor_position=6)
        completions = comp.get_completions(mock_document, None)
        self.assertEqual(len(list(completions)), 2)

        mock_document = Document(text='ln  foo', cursor_position=3)
        completions = comp.get_completions(mock_document, None)
        self.assertEqual(len(list(completions)), 2)

        mock_document = Document(text='ln  foo bar', cursor_position=3)
        completions = comp.get_completions(mock_document, None)
        self.assertEqual(len(list(completions)), 0)

        mock_document = Document(text='ln foo bar', cursor_position=6)
        completions = comp.get_completions(mock_document, None)
        self.assertEqual(len(list(completions)), 1)

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_fq_name_completion(self, mock_session):
        mock_document = Document(text='cat bar/default-dom')

        comp = ShellCompleter()
        r1 = Resource('bar', fq_name='default-domain:project:resource')
        r2 = Resource('bar', fq_name='foo:foo:foo')

        completions = list(comp.get_completions(mock_document, None))
        self.assertEqual(len(completions), 1)
        self.assertTrue(str(r1.path.relative_to(Context().shell.current_path)) in
                        [c.text for c in completions])

        r1.delete()
        r2.delete()
        completions = comp.get_completions(mock_document, None)
        self.assertEqual(len(list(completions)), 0)

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_not_found(self, mock_session):
        mock_session.id_to_fqname.side_effect = HttpError(http_status=404)
        mock_document = Document(text='cat foo')

        comp = ShellCompleter()
        try:
            Resource('foo', uuid='dda4574d-96bc-43fd-bdf7-12ac776f754c', check=True)
        except ResourceNotFound:
            pass
        completions = list(comp.get_completions(mock_document, None))
        self.assertEqual(len(completions), 0)


if __name__ == "__main__":
    unittest.main()
