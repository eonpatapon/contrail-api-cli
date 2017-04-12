from __future__ import unicode_literals
import sys
import unittest
import uuid
import io
try:
    import mock
except ImportError:
    import unittest.mock as mock

import contrail_api_cli.command as cmds
from contrail_api_cli import client
from contrail_api_cli.utils import Path, FQName
from contrail_api_cli.context import Context
from contrail_api_cli.resource import Resource, Collection
from contrail_api_cli.exceptions import ResourceNotFound, CommandError
from contrail_api_cli.schema import create_schema_from_version, DummySchema
from contrail_api_cli.manager import CommandManager

from .utils import CLITest


class Cmd(cmds.Command):
    description = "Not a real command"

    def __call__(self):
        if self._is_piped:
            return "piped"
        else:
            return "not piped"


class ArgTest(cmds.Command):
    arg = cmds.Arg()

    def __call__(self, arg=None):
        return arg


class TestCommand(CLITest):

    def setUp(self):
        CLITest.setUp(self)
        self.mgr = CommandManager()
        self.mgr.load_namespace('contrail_api_cli.shell_command')
        self.mgr.add('cmd', Cmd('cmd'))
        self.mgr.add('arg-test', ArgTest('arg-test'))

    def test_cd(self):
        self.mgr.get('cd')('foo')
        self.assertEqual(Context().shell.current_path, Path('/foo'))
        self.mgr.get('cd')('bar')
        self.assertEqual(Context().shell.current_path, Path('/foo/bar'))
        self.mgr.get('cd')('..')
        self.assertEqual(Context().shell.current_path, Path('/foo'))
        self.mgr.get('cd')('')
        self.assertEqual(Context().shell.current_path, Path('/foo'))
        self.mgr.get('cd')('/')
        self.assertEqual(Context().shell.current_path, Path('/'))

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_root_collection(self, mock_session):
        Context().shell.current_path = Path('/')
        mock_session.get_json.return_value = {
            'href': self.BASE,
            'links': [
                {'link': {'href': self.BASE + '/instance-ips',
                          'path': Path('/instance-ips'),
                          'name': 'instance-ip',
                          'rel': 'collection'}},
                {'link': {'href': self.BASE + '/instance-ip',
                          'path': Path('/instance-ip'),
                          'name': 'instance-ip',
                          'rel': 'resource-base'}}
            ]
        }
        result = self.mgr.get('ls')()
        self.assertEqual('instance-ip', result)

        mock_session.get_json.side_effect = [
            {
                'href': self.BASE,
                'links': [
                    {'link': {'href': self.BASE + '/foos',
                              'path': Path('/foos'),
                              'name': 'foo',
                              'rel': 'collection'}},
                    {'link': {'href': self.BASE + '/bars',
                              'path': Path('/bars'),
                              'name': 'bar',
                              'rel': 'collection'}}
                ]
            },
            {
                'foos': [
                    {'href': self.BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                     'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724'},
                    {'href': self.BASE + '/foo/c2588045-d6fb-4f37-9f46-9451f653fb6a',
                     'uuid': 'c2588045-d6fb-4f37-9f46-9451f653fb6a'}
                ]
            },
            {
                'bars': [
                    {'href': self.BASE + '/bar/ffe8de43-a141-4336-8d70-bf970813bbf7',
                     'uuid': 'ffe8de43-a141-4336-8d70-bf970813bbf7'}
                ]
            }
        ]

        Context().shell.current_path = Path('/')
        expected_result = """foo/ec1afeaa-8930-43b0-a60a-939f23a50724
foo/c2588045-d6fb-4f37-9f46-9451f653fb6a
bar/ffe8de43-a141-4336-8d70-bf970813bbf7"""
        result = self.mgr.get('ls')(paths=['*'])
        self.assertEqual(result, expected_result)

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_resource_collection(self, mock_session):
        mock_session.get_json.return_value = {
            'foos': [
                {'href': self.BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                 'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724'},
                {'href': self.BASE + '/foo/c2588045-d6fb-4f37-9f46-9451f653fb6a',
                 'uuid': 'c2588045-d6fb-4f37-9f46-9451f653fb6a'}
            ]
        }

        Context().shell.current_path = Path('/foo')
        result = self.mgr.get('ls')()
        self.assertEqual('\n'.join(['ec1afeaa-8930-43b0-a60a-939f23a50724',
                                    'c2588045-d6fb-4f37-9f46-9451f653fb6a']),
                         result)

        Context().shell.current_path = Path('/')
        result = self.mgr.get('ls')(paths=['foo'])
        self.assertEqual('\n'.join(['foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                                    'foo/c2588045-d6fb-4f37-9f46-9451f653fb6a']),
                         result)

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_resource_ls(self, mock_session):
        mock_session.get_json.return_value = {
            'foo': {
                'href': self.BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724',
            }
        }
        Context().shell.current_path = Path('/foo')
        expected_result = 'ec1afeaa-8930-43b0-a60a-939f23a50724'
        result = self.mgr.get('ls')(paths=['ec1afeaa-8930-43b0-a60a-939f23a50724'])
        self.assertEqual(result, expected_result)

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_resource_long_ls(self, mock_session):
        mock_session.id_to_fqname.return_value = {
            'type': 'foo',
            'fq_name': FQName('default-project:foo:ec1afeaa-8930-43b0-a60a-939f23a50724')
        }
        mock_session.get_json.return_value = {
            'foo': {
                'href': self.BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724',
                'fq_name': ['default-project', 'foo', 'ec1afeaa-8930-43b0-a60a-939f23a50724'],
                'prop': {
                    'foo': False,
                    'bar': [1, 2, 3]
                }
            }
        }
        Context().shell.current_path = Path('/')
        result = self.mgr.get('ls')(paths=['foo/ec1afeaa-8930-43b0-a60a-939f23a50724'],
                                    long=True)
        expected_result = "foo/ec1afeaa-8930-43b0-a60a-939f23a50724  default-project:foo:ec1afeaa-8930-43b0-a60a-939f23a50724"
        self.assertEqual(result, expected_result)

        Context().shell.current_path = Path('/foo')
        result = self.mgr.get('ls')(paths=['ec1afeaa-8930-43b0-a60a-939f23a50724'],
                                    long=True, fields=['prop'])
        expected_results = ["ec1afeaa-8930-43b0-a60a-939f23a50724  foo=False|bar=1,2,3",
                            "ec1afeaa-8930-43b0-a60a-939f23a50724  bar=1,2,3|foo=False"]

        self.assertTrue(any([result == r for r in expected_results]))

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_resource_parent_uuid_ls(self, mock_session):
        mock_session.configure_mock(base_url=self.BASE)
        self.mgr.get('ls')(paths=['foo'])
        mock_session.get_json.assert_called_with(self.BASE + '/foos')
        self.mgr.get('ls')(paths=['foo'], parent_uuid='1ad831be-3b21-4870-aadf-8efc2b0a480d')
        mock_session.get_json.assert_called_with(self.BASE + '/foos', parent_id='1ad831be-3b21-4870-aadf-8efc2b0a480d')

    @mock.patch('contrail_api_cli.commands.cat.highlight_json')
    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_resource_cat(self, mock_session, mock_highlight_json):
        # bind original method to mock_session
        mock_session.id_to_fqname = client.ContrailAPISession.id_to_fqname.__get__(mock_session)
        mock_session.make_url = client.ContrailAPISession.make_url.__get__(mock_session)

        # called by id_to_fqname
        def post(url, json=None):
            if json['uuid'] == "ec1afeaa-8930-43b0-a60a-939f23a50724":
                return {
                    "type": "foo",
                    "fq_name": [
                        "foo",
                        "ec1afeaa-8930-43b0-a60a-939f23a50724"
                    ]
                }
            if json['uuid'] == "15315402-8a21-4116-aeaa-b6a77dceb191":
                return {
                    "type": "bar",
                    "fq_name": [
                        "bar",
                        "15315402-8a21-4116-aeaa-b6a77dceb191"
                    ]
                }

        mock_session.post_json.side_effect = post
        mock_highlight_json.side_effect = lambda d: d
        mock_session.get_json.return_value = {
            'foo': {
                'href': self.BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724',
                'attr': None,
                'fq_name': [
                    'foo',
                    'ec1afeaa-8930-43b0-a60a-939f23a50724'
                ],
                'bar_refs': [
                    {
                        'href': self.BASE + '/bar/15315402-8a21-4116-aeaa-b6a77dceb191',
                        'uuid': '15315402-8a21-4116-aeaa-b6a77dceb191',
                        'to': [
                            'bar',
                            '15315402-8a21-4116-aeaa-b6a77dceb191'
                        ]
                    }
                ]
            }
        }
        Context().shell.current_path = Path('/foo')
        expected_resource = Resource('foo', uuid='ec1afeaa-8930-43b0-a60a-939f23a50724',
                                     href=self.BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                                     attr=None, fq_name='foo:ec1afeaa-8930-43b0-a60a-939f23a50724')
        expected_resource['bar_refs'] = [
            Resource('bar', uuid='15315402-8a21-4116-aeaa-b6a77dceb191',
                     href=self.BASE + '/bar/15315402-8a21-4116-aeaa-b6a77dceb191',
                     to=['bar', '15315402-8a21-4116-aeaa-b6a77dceb191'])
        ]
        result = self.mgr.get('cat')(paths=['ec1afeaa-8930-43b0-a60a-939f23a50724'])
        self.assertEqual(expected_resource.json(), result)

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_notfound_fqname_ls(self, mock_session):
        fq_name = 'default-domain:foo'
        Context().shell.current_path = Path('/foo')
        mock_session.fqname_to_id.side_effect = client.HttpError(http_status=404)
        with self.assertRaises(ResourceNotFound) as e:
            self.mgr.get('ls')(paths=[fq_name])
            self.assertEqual("%s doesn't exists" % fq_name, str(e))
        self.assertFalse(mock_session.get_json.called)

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_count(self, mock_session):
        mock_session.get_json.return_value = {
            'foos': {
                'count': 3
            }
        }

        Context().shell.current_path = Path('/foo')
        result = self.mgr.get('du')()
        self.assertEqual(result, '3')

        Context().shell.current_path = Path('/')
        result = self.mgr.get('du')(paths=['foo'])
        self.assertEqual(result, '3')

        Context().shell.current_path = Path('/foo/%s' % uuid.uuid4())
        with self.assertRaises(CommandError):
            self.mgr.get('du')()

    @mock.patch('contrail_api_cli.resource.Context.session')
    @mock.patch('contrail_api_cli.commands.rm.continue_prompt')
    def test_rm(self, mock_continue_prompt, mock_session):
        mock_session.configure_mock(base_url=self.BASE)
        Context().shell.current_path = Path('/')
        t = ['foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f']
        mock_session.delete.return_value = True
        self.mgr.get('rm')(paths=t, force=True)
        mock_session.delete.assert_has_calls([
            mock.call(self.BASE + '/foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f')
        ])
        self.assertFalse(mock_continue_prompt.called)

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_rm_multiple_resources(self, mock_session):
        mock_session.configure_mock(base_url=self.BASE)
        Context().shell.current_path = Path('/foo')
        ts = ['6b6a7f47-807e-4c39-8ac6-3adcf2f5498f',
              '22916187-5b6f-40f1-b7b6-fc6fe9f23bce']
        mock_session.delete.return_value = True
        self.mgr.get('rm')(paths=ts, force=True)
        mock_session.delete.assert_has_calls([
            mock.call(self.BASE + '/foo/22916187-5b6f-40f1-b7b6-fc6fe9f23bce'),
            mock.call(self.BASE + '/foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f')
        ])

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_rm_wildcard_resources(self, mock_session):
        mock_session.configure_mock(base_url=self.BASE)
        Context().shell.current_path = Path('/foo')
        mock_session.get_json.return_value = {
            'foos': [
                {'href': self.BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                 'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724',
                 'fq_name': ['default', 'foo', '1']},
                {'href': self.BASE + '/foo/c2588045-d6fb-4f37-9f46-9451f653fb6a',
                 'uuid': 'c2588045-d6fb-4f37-9f46-9451f653fb6a',
                 'fq_name': ['default', 'foo', '1']}
            ]
        }
        mock_session.delete.return_value = True
        t = ['ec1afeaa-8930*', 'c2588045-d6fb-4f37-9f46-9451f653fb6a']
        self.mgr.get('rm')(paths=t, force=True)
        mock_session.delete.assert_has_calls([
            mock.call(self.BASE + '/foo/c2588045-d6fb-4f37-9f46-9451f653fb6a'),
            mock.call(self.BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724')
        ])
        t = ['*', 'c2588045-d6fb-4f37-9f46-9451f653fb6a']
        self.mgr.get('rm')(paths=t, force=True)
        mock_session.delete.assert_has_calls([
            mock.call(self.BASE + '/foo/c2588045-d6fb-4f37-9f46-9451f653fb6a'),
            mock.call(self.BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724')
        ])
        t = ['default:*', 'c2588045-d6fb-4f37-9f46-9451f653fb6a']
        self.mgr.get('rm')(paths=t, force=True)
        mock_session.delete.assert_has_calls([
            mock.call(self.BASE + '/foo/c2588045-d6fb-4f37-9f46-9451f653fb6a'),
            mock.call(self.BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724')
        ])

    @mock.patch('contrail_api_cli.resource.Context.session')
    @mock.patch('contrail_api_cli.commands.rm.continue_prompt')
    def test_rm_noconfirm(self, mock_continue_prompt, mock_session):
        Context().shell.current_path = Path('/')
        mock_continue_prompt.return_value = False
        t = ['foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f']
        self.mgr.get('rm')(paths=t)
        self.assertFalse(mock_session.delete.called)

    @mock.patch('contrail_api_cli.resource.Context.session')
    @mock.patch('contrail_api_cli.commands.rm.continue_prompt')
    def test_rm_recursive(self, mock_continue_prompt, mock_session):
        Context().shell.current_path = Path('/')
        Collection('bar')
        Collection('foobar')
        t = ['foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f']
        mock_continue_prompt.return_value = True
        mock_session.configure_mock(base_url=self.BASE)
        mock_session.get_json.side_effect = [
            {
                'foo': {
                    'href': self.BASE + '/foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f',
                    'uuid': '6b6a7f47-807e-4c39-8ac6-3adcf2f5498f',
                    'bar_back_refs': [
                        {
                            'href': self.BASE + '/bar/22916187-5b6f-40f1-b7b6-fc6fe9f23bce',
                            'uuid': '22916187-5b6f-40f1-b7b6-fc6fe9f23bce',
                            'to': [
                                'bar',
                                '22916187-5b6f-40f1-b7b6-fc6fe9f23bce'
                            ]
                        },
                        {
                            'href': self.BASE + '/bar/776bdf88-6283-4c4b-9392-93a857807307',
                            'uuid': '776bdf88-6283-4c4b-9392-93a857807307',
                            'to': [
                                'bar',
                                '776bdf88-6283-4c4b-9392-93a857807307'
                            ]
                        }
                    ]
                }
            },
            {
                'bar': {
                    'href': self.BASE + '/bar/22916187-5b6f-40f1-b7b6-fc6fe9f23bce',
                    'uuid': '22916187-5b6f-40f1-b7b6-fc6fe9f23bce',
                    'foobar_back_refs': [
                        {
                            'href': self.BASE + '/foobar/1050223f-a230-4ed6-96f1-c332700c5e01',
                            'to': [
                                'foobar',
                                '1050223f-a230-4ed6-96f1-c332700c5e01'
                            ],
                            'uuid': '1050223f-a230-4ed6-96f1-c332700c5e01'
                        }
                    ]
                }
            },
            {
                'foobar': {
                    'href': self.BASE + '/foobar/1050223f-a230-4ed6-96f1-c332700c5e01',
                    'uuid': '1050223f-a230-4ed6-96f1-c332700c5e01'
                }
            },
            {
                'bar': {
                    'href': self.BASE + '/bar/776bdf88-6283-4c4b-9392-93a857807307',
                    'uuid': '776bdf88-6283-4c4b-9392-93a857807307'
                }
            }
        ]
        mock_session.delete.return_value = True
        self.mgr.get('rm')(paths=t, recursive=True)
        expected_calls = [
            mock.call.delete(self.BASE + '/bar/776bdf88-6283-4c4b-9392-93a857807307'),
            mock.call.delete(self.BASE + '/foobar/1050223f-a230-4ed6-96f1-c332700c5e01'),
            mock.call.delete(self.BASE + '/bar/22916187-5b6f-40f1-b7b6-fc6fe9f23bce'),
            mock.call.delete(self.BASE + '/foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f')
        ]
        mock_session.delete.assert_has_calls(expected_calls)

    @mock.patch('contrail_api_cli.resource.Context.session')
    @mock.patch('contrail_api_cli.commands.shell.prompt')
    def test_pipes(self, mock_prompt, mock_session):
        old_stdout = sys.stdout
        out = io.BytesIO()
        sys.stdout = out
        mock_prompt.side_effect = [
            "cmd | grep piped",
            "cmd",
            "exit"
        ]
        self.mgr.get('shell')()
        sys.stdout = old_stdout
        result = out.getvalue()
        self.assertEqual(result, b'piped\nnot piped\n')

    @mock.patch('contrail_api_cli.resource.Context.session')
    @mock.patch('contrail_api_cli.commands.shell.prompt')
    def test_shell_args(self, mock_prompt, mock_session):
        old_stdout = sys.stdout
        out = io.BytesIO()
        sys.stdout = out
        mock_prompt.side_effect = [
            "arg-test \"foo  bar\"",
            "exit"
        ]
        self.mgr.get('shell')()
        sys.stdout = old_stdout
        result = out.getvalue()
        self.assertEqual(result, b'foo  bar\n')

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_ln(self, mock_session):
        Context().schema = create_schema_from_version('2.21')
        r1 = Resource('virtual-network', uuid='9174e7d3-865b-4faf-ab0f-c083e43fee6d')
        r2 = Resource('route-table', uuid='9174e7d3-865b-4faf-ab0f-c083e43fee6d')
        r3 = Resource('project', uuid='9174e7d3-865b-4faf-ab0f-c083e43fee6d')
        r5 = Resource('logical-router', uuid='9174e7d3-865b-4faf-ab0f-c083e43fee6d')
        self.mgr.get('ln')(resources=[r1.path, r2.path])
        self.mgr.get('ln')(resources=[r1.path, r2.path], remove=True)
        self.mgr.get('ln')(resources=[r1.path, r5.path])
        self.mgr.get('ln')(resources=[r1.path, r5.path], remove=True)
        with self.assertRaises(CommandError):
            self.mgr.get('ln')(resources=[r1.path, r3.path])
        with self.assertRaises(CommandError):
            self.mgr.get('ln')(resources=['foo/9174e7d3-865b-4faf-ab0f-c083e43fee6d', r1.path])
        Context().schema = DummySchema()

    def test_schema(self):
        self.mgr.get('schema')(schema_version='2.21')
        self.mgr.get('schema')(schema_version='2.21', resource_name='virtual-network')
        self.mgr.get('schema')(schema_version='2.21', resource_name='route-target')
        with self.assertRaises(CommandError):
            self.mgr.get('schema')(schema_version='2.21', resource_name='foo')
        with self.assertRaises(CommandError):
            self.mgr.get('schema')(schema_version='4.0', resource_name='route-target')
        self.mgr.get('schema')(schema_version='4.0', list_version=True)


if __name__ == '__main__':
    unittest.main()
