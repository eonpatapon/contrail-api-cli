import sys
import unittest
import uuid
try:
    import mock
except ImportError:
    import unittest.mock as mock
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import contrail_api_cli.commands as cmds
from contrail_api_cli import client
from contrail_api_cli.utils import Path, ShellContext
from contrail_api_cli.resource import Resource


BASE = 'http://localhost:8082'


class Cmd(cmds.Command):
    description = "Not a real command"

    def __call__(self):
        if self._is_piped:
            return "piped"
        else:
            return "not piped"


class TestCommands(unittest.TestCase):

    def test_cd(self):
        cmds.get_command('cd')('foo')
        self.assertEqual(ShellContext.current_path, Path('/foo'))
        cmds.get_command('cd')('bar')
        self.assertEqual(ShellContext.current_path, Path('/foo/bar'))
        cmds.get_command('cd')('..')
        self.assertEqual(ShellContext.current_path, Path('/foo'))
        cmds.get_command('cd')('')
        self.assertEqual(ShellContext.current_path, Path('/foo'))
        cmds.get_command('cd')('/')
        self.assertEqual(ShellContext.current_path, Path('/'))

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_root_collection(self, mock_session):
        ShellContext.current_path = Path('/')
        mock_session.get_json.return_value = {
            'href': BASE,
            'links': [
                {'link': {'href': BASE + '/instance-ips',
                          'path': Path('/instance-ips'),
                          'name': 'instance-ip',
                          'rel': 'collection'}},
                {'link': {'href': BASE + '/instance-ip',
                          'path': Path('/instance-ip'),
                          'name': 'instance-ip',
                          'rel': 'resource-base'}}
            ]
        }
        result = cmds.get_command('ls')()
        self.assertEqual('instance-ip', result)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_collection(self, mock_session):
        mock_session.get_json.return_value = {
            'instance-ips': [
                {'href': BASE + '/instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724',
                 'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724'},
                {'href': BASE + '/instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a',
                 'uuid': 'c2588045-d6fb-4f37-9f46-9451f653fb6a'}
            ]
        }

        ShellContext.current_path = Path('/instance-ip')
        result = cmds.get_command('ls')()
        self.assertEqual('\n'.join(['ec1afeaa-8930-43b0-a60a-939f23a50724',
                                    'c2588045-d6fb-4f37-9f46-9451f653fb6a']),
                         result)

        ShellContext.current_path = Path('/')
        result = cmds.get_command('ls')(paths=['instance-ip'])
        self.assertEqual('\n'.join(['instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724',
                                    'instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a']),
                         result)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_ls(self, mock_session):
        mock_session.get_json.return_value = {
            'foo': {
                'href': BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724',
            }
        }
        ShellContext.current_path = Path('/foo')
        expected_result = 'ec1afeaa-8930-43b0-a60a-939f23a50724'
        result = cmds.get_command('ls')(paths=['ec1afeaa-8930-43b0-a60a-939f23a50724'])
        self.assertEqual(result, expected_result)

    @mock.patch('contrail_api_cli.commands.Cat.colorize')
    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_resource_cat(self, mock_session, mock_colorize):
        # bind original method to mock_session
        mock_session.id_to_fqname = client.ContrailAPISession.id_to_fqname.__get__(mock_session)
        mock_session.make_url = client.ContrailAPISession.make_url.__get__(mock_session)

        # called by id_to_fqname
        def post(url, json=None):
            if json['type'] == "foo":
                return {
                    "fq_name": [
                        "foo",
                        "ec1afeaa-8930-43b0-a60a-939f23a50724"
                    ]
                }
            if json['type'] == "bar":
                return {
                    "fq_name": [
                        "bar",
                        "15315402-8a21-4116-aeaa-b6a77dceb191"
                    ]
                }

        mock_session.post_json.side_effect = post
        mock_colorize.side_effect = lambda d: d
        mock_session.get_json.return_value = {
            'foo': {
                'href': BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724',
                'attr': None,
                'fq_name': [
                    'foo',
                    'ec1afeaa-8930-43b0-a60a-939f23a50724'
                ],
                'bar_refs': [
                    {
                        'href': BASE + '/bar/15315402-8a21-4116-aeaa-b6a77dceb191',
                        'uuid': '15315402-8a21-4116-aeaa-b6a77dceb191',
                        'to': [
                            'bar',
                            '15315402-8a21-4116-aeaa-b6a77dceb191'
                        ]
                    }
                ]
            }
        }
        ShellContext.current_path = Path('/foo')
        expected_resource = Resource('foo', uuid='ec1afeaa-8930-43b0-a60a-939f23a50724',
                                     href=BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                                     attr=None, fq_name='foo:ec1afeaa-8930-43b0-a60a-939f23a50724')
        expected_resource['bar_refs'] = [
            Resource('bar', uuid='15315402-8a21-4116-aeaa-b6a77dceb191',
                     href=BASE + '/bar/15315402-8a21-4116-aeaa-b6a77dceb191',
                     fq_name='bar:15315402-8a21-4116-aeaa-b6a77dceb191')
        ]
        expected_json = client.to_json(expected_resource, cls=cmds.RelativeResourceEncoder)
        result = cmds.get_command('cat')(paths=['ec1afeaa-8930-43b0-a60a-939f23a50724'])
        self.assertEqual(expected_json, result)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_notfound_fqname_ls(self, mock_session):
        fq_name = 'default-domain:foo'
        ShellContext.current_path = Path('foo')
        mock_session.fqname_to_id.return_value = None
        with self.assertRaises(cmds.CommandError) as e:
            cmds.get_command('ls')(paths=[fq_name])
            self.assertEqual("%s doesn't exists" % fq_name, str(e))
        self.assertFalse(mock_session.get_json.called)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_count(self, mock_session):
        mock_session.get_json.return_value = {
            'foos': {
                'count': 3
            }
        }

        ShellContext.current_path = Path('/foo')
        result = cmds.get_command('count')()
        self.assertEqual(result, '3')

        ShellContext.current_path = Path('/')
        result = cmds.get_command('count')(paths=['foo'])
        self.assertEqual(result, '3')

        ShellContext.current_path = Path('/foo/%s' % uuid.uuid4())
        with self.assertRaises(cmds.CommandError) as e:
            cmds.get_command('count')()
            self.assertEqual(". is not a collection", str(e))

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    @mock.patch('contrail_api_cli.commands.continue_prompt')
    def test_rm(self, mock_continue_prompt, mock_session):
        mock_session.configure_mock(base_url=BASE)
        ShellContext.current_path = Path('/')
        t = ['foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f']
        mock_session.delete.return_value = True
        cmds.get_command('rm')(paths=t, force=True)
        mock_session.delete.assert_has_calls([
            mock.call(BASE + '/foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f')
        ])
        self.assertFalse(mock_continue_prompt.called)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_rm_multiple_resources(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        ShellContext.current_path = Path('/foo')
        ts = ['6b6a7f47-807e-4c39-8ac6-3adcf2f5498f',
              '22916187-5b6f-40f1-b7b6-fc6fe9f23bce']
        mock_session.delete.return_value = True
        cmds.get_command('rm')(paths=ts, force=True)
        mock_session.delete.assert_has_calls([
            mock.call(BASE + '/foo/22916187-5b6f-40f1-b7b6-fc6fe9f23bce'),
            mock.call(BASE + '/foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f')
        ])

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_rm_wildcard_resources(self, mock_session):
        mock_session.configure_mock(base_url=BASE)
        ShellContext.current_path = Path('/foo')
        mock_session.get_json.return_value = {
            'foos': [
                {'href': BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724',
                 'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724'},
                {'href': BASE + '/foo/c2588045-d6fb-4f37-9f46-9451f653fb6a',
                 'uuid': 'c2588045-d6fb-4f37-9f46-9451f653fb6a'}
            ]
        }
        mock_session.delete.return_value = True
        t = ['ec1afeaa-8930*', 'c2588045-d6fb-4f37-9f46-9451f653fb6a']
        cmds.get_command('rm')(paths=t, force=True)
        mock_session.delete.assert_has_calls([
            mock.call(BASE + '/foo/c2588045-d6fb-4f37-9f46-9451f653fb6a'),
            mock.call(BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724')
        ])
        t = ['*', 'c2588045-d6fb-4f37-9f46-9451f653fb6a']
        cmds.get_command('rm')(paths=t, force=True)
        mock_session.delete.assert_has_calls([
            mock.call(BASE + '/foo/c2588045-d6fb-4f37-9f46-9451f653fb6a'),
            mock.call(BASE + '/foo/ec1afeaa-8930-43b0-a60a-939f23a50724')
        ])

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    @mock.patch('contrail_api_cli.commands.continue_prompt')
    def test_rm_noconfirm(self, mock_continue_prompt, mock_session):
        ShellContext.current_path = Path('/')
        mock_continue_prompt.return_value = False
        t = ['foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f']
        cmds.get_command('rm')(paths=t)
        self.assertFalse(mock_session.delete.called)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    @mock.patch('contrail_api_cli.commands.continue_prompt')
    def test_rm_recursive(self, mock_continue_prompt, mock_session):
        ShellContext.current_path = Path('/')
        t = ['foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f']
        mock_continue_prompt.return_value = True
        mock_session.configure_mock(base_url=BASE)
        mock_session.get_json.side_effect = [
            {
                'foo': {
                    'href': BASE + '/foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f',
                    'bar_back_refs': [
                        {
                            'href': BASE + '/bar/22916187-5b6f-40f1-b7b6-fc6fe9f23bce',
                            'uuid': '22916187-5b6f-40f1-b7b6-fc6fe9f23bce',
                            'to': [
                                'bar',
                                '22916187-5b6f-40f1-b7b6-fc6fe9f23bce'
                            ]
                        },
                        {
                            'href': BASE + '/bar/776bdf88-6283-4c4b-9392-93a857807307',
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
                    'href': BASE + '/bar/22916187-5b6f-40f1-b7b6-fc6fe9f23bce',
                    'uuid': '22916187-5b6f-40f1-b7b6-fc6fe9f23bce',
                    'foobar_back_refs': [
                        {
                            'href': BASE + '/foobar/1050223f-a230-4ed6-96f1-c332700c5e01',
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
                    'href': BASE + '/foobar/1050223f-a230-4ed6-96f1-c332700c5e01',
                    'uuid': '1050223f-a230-4ed6-96f1-c332700c5e01'
                }
            },
            {
                'bar': {
                    'href': BASE + '/bar/776bdf88-6283-4c4b-9392-93a857807307',
                    'uuid': '776bdf88-6283-4c4b-9392-93a857807307'
                }
            }
        ]
        mock_session.delete.return_value = True
        cmds.get_command('rm')(paths=t, recursive=True)
        expected_calls = [
            mock.call.delete(BASE + '/bar/776bdf88-6283-4c4b-9392-93a857807307'),
            mock.call.delete(BASE + '/foobar/1050223f-a230-4ed6-96f1-c332700c5e01'),
            mock.call.delete(BASE + '/bar/22916187-5b6f-40f1-b7b6-fc6fe9f23bce'),
            mock.call.delete(BASE + '/foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f')
        ]
        mock_session.delete.assert_has_calls(expected_calls)

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    @mock.patch('contrail_api_cli.commands.prompt')
    def test_pipes(self, mock_prompt, mock_session):
        old_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        mock_prompt.side_effect = [
            "cmd | grep piped",
            "cmd",
            "exit"
        ]
        cmds.get_command('shell')()
        sys.stdout = old_stdout
        result = out.getvalue().strip()
        self.assertEqual(result, "piped\nnot piped")

if __name__ == '__main__':
    unittest.main()
