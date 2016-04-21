from __future__ import unicode_literals
import unittest
try:
    import mock
except ImportError:
    import unittest.mock as mock

from keystoneclient.exceptions import HttpError

from contrail_api_cli.command import ShellContext, ShellCompleter
from contrail_api_cli.resource import Resource
from contrail_api_cli.utils import Path
from contrail_api_cli.exceptions import ResourceNotFound

BASE = 'http://localhost:8082'


class TestCompleter(unittest.TestCase):

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_add_del_resource(self, mock_session):
        ShellContext.current_path = Path('/')
        mock_document = mock.Mock()
        mock_document.get_word_before_cursor.return_value = 'bar'
        mock_document.configure_mock(text='ls bar')

        comp = ShellCompleter()
        r1 = Resource('foo', uuid='d8eb36b4-9c57-49c5-9eac-95bedc90eb9a')
        r2 = Resource('bar', uuid='4c6d3711-61f1-4505-b8df-189d32b52872')
        completions = comp.get_completions(mock_document, None)
        self.assertTrue(str(r2.path.relative_to(ShellContext.current_path)) in
                        [c.text for c in completions])

        r1.delete()
        r2.delete()
        completions = comp.get_completions(mock_document, None)
        self.assertTrue(str(r2.path.relative_to(ShellContext.current_path)) not in
                        [c.text for c in completions])

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_add_same_resource(self, mock_session):
        ShellContext.current_path = Path('/')
        mock_document = mock.Mock()
        mock_document.get_word_before_cursor.return_value = 'bar'
        mock_document.configure_mock(text='ls bar')

        comp = ShellCompleter()
        r1 = Resource('bar', uuid='4c6d3711-61f1-4505-b8df-189d32b52872')
        r2 = Resource('bar', uuid='4c6d3711-61f1-4505-b8df-189d32b52872')
        completions = comp.get_completions(mock_document, None)
        self.assertEqual(len(list(completions)), 1)
        r1.delete()
        completions = comp.get_completions(mock_document, None)
        self.assertEqual(len(list(completions)), 0)
        r2.delete()

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_fq_name_completion(self, mock_session):
        ShellContext.current_path = Path('/')
        mock_document = mock.Mock()
        mock_document.get_word_before_cursor.return_value = 'default-dom'
        mock_document.configure_mock(text='ls default-dom')

        comp = ShellCompleter()
        r1 = Resource('bar', fq_name='default-domain:project:resource')
        r2 = Resource('foo', fq_name='foo:foo:foo')

        completions = list(comp.get_completions(mock_document, None))
        self.assertEqual(len(completions), 1)
        self.assertTrue(str(r1.path.relative_to(ShellContext.current_path)) in
                        [c.text for c in completions])

        r1.delete()
        r2.delete()
        completions = comp.get_completions(mock_document, None)
        self.assertEqual(len(list(completions)), 0)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_not_found(self, mock_session):
        mock_session.id_to_fqname.side_effect = HttpError(http_status=404)
        mock_document = mock.Mock()
        mock_document.get_word_before_cursor.return_value = 'foo'
        mock_document.configure_mock(text='ls foo')

        comp = ShellCompleter()
        try:
            Resource('foo', uuid='dda4574d-96bc-43fd-bdf7-12ac776f754c', check=True)
        except ResourceNotFound:
            pass
        completions = list(comp.get_completions(mock_document, None))
        self.assertEqual(len(completions), 0)


if __name__ == "__main__":
    unittest.main()
