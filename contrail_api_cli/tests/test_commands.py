import unittest
import uuid
try:
    import mock
except ImportError:
    import unittest.mock as mock

import contrail_api_cli.commands as cmds
from contrail_api_cli import client
from contrail_api_cli.utils import Path, ShellContext, Collection, Resource


BASE = 'http://localhost:8082'


class TestCommands(unittest.TestCase):

    def test_cd(self):
        cmds.cd('foo')
        self.assertEqual(ShellContext.current_path, Path('/foo'))
        cmds.cd('bar')
        self.assertEqual(ShellContext.current_path, Path('/foo/bar'))
        cmds.cd('..')
        self.assertEqual(ShellContext.current_path, Path('/foo'))
        cmds.cd('')
        self.assertEqual(ShellContext.current_path, Path('/foo'))
        cmds.cd('/')
        self.assertEqual(ShellContext.current_path, Path('/'))

    @mock.patch('contrail_api_cli.utils.ResourceBase.session')
    def test_root_collection(self, mock_session):
        mock_session.get.return_value = {
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
        result = cmds.ls()
        self.assertEqual('instance-ip', result)

    @mock.patch('contrail_api_cli.utils.ResourceBase.session')
    def test_resource_collection(self, mock_session):
        mock_session.get.return_value = {
            'instance-ips': [
                {'href': BASE + '/instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724',
                 'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724'},
                {'href': BASE + '/instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a',
                 'uuid': 'c2588045-d6fb-4f37-9f46-9451f653fb6a'}
            ]
        }

        ShellContext.current_path = Path('/instance-ip')
        result = cmds.ls()
        self.assertEqual('\n'.join(['ec1afeaa-8930-43b0-a60a-939f23a50724',
                                    'c2588045-d6fb-4f37-9f46-9451f653fb6a']),
                         result)

        ShellContext.current_path = Path('/')
        result = cmds.ls(resource='instance-ip')
        self.assertEqual('\n'.join(['instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724',
                                    'instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a']),
                         result)

    @mock.patch('contrail_api_cli.commands.Ls.colorize')
    @mock.patch('contrail_api_cli.utils.ResourceBase.session')
    def test_resource_ls(self, mock_session, mock_colorize):
        mock_colorize.side_effect = lambda d: d
        mock_session.get.return_value = {
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
                        'href': BASE + '/bar/ec1afeaa-8930-43b0-a60a-939f23a50724',
                        'uuid': 'ec1afeaa-8930-43b0-a60a-939f23a50724',
                        'to': [
                            'bar',
                            'ec1afeaa-8930-43b0-a60a-939f23a50724'
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
            Resource('bar', uuid='ec1afeaa-8930-43b0-a60a-939f23a50724',
                     href=BASE + '/bar/ec1afeaa-8930-43b0-a60a-939f23a50724',
                     fq_name='bar:ec1afeaa-8930-43b0-a60a-939f23a50724')
        ]
        expected_json = client.to_json(expected_resource, cls=cmds.RelativeResourceEncoder)
        result = cmds.ls(resource='ec1afeaa-8930-43b0-a60a-939f23a50724')
        self.assertEqual(expected_json, result)
        # self.assertEqual(result, expected_resource)
        # self.assertEqual(result.fq_name, 'foo:ec1afeaa-8930-43b0-a60a-939f23a50724')
        # found_paths = []
        # while not ShellContext.completion_queue.empty():
        # found_paths.append(ShellContext.completion_queue.get().path)
        # self.assertIn(Path('/bar/ec1afeaa-8930-43b0-a60a-939f23a50724'), found_paths)

    @mock.patch('contrail_api_cli.utils.ResourceBase.session')
    def test_notfound_fqname_ls(self, mock_session):
        fq_name = 'default-domain:foo'
        ShellContext.current_path = Path('foo')
        mock_session.fqname_to_id.return_value = None
        result = cmds.ls(resource=fq_name)
        self.assertEqual("%s doesn't exists" % fq_name, result)
        self.assertFalse(mock_session.get.called)

    @mock.patch('contrail_api_cli.utils.ResourceBase.session')
    def test_count(self, mock_session):
        ShellContext.current_path = Path('/foo')
        mock_session.get.return_value = {
            'foos': {
                'count': 3
            }
        }

        c = Collection('foo')
        self.assertEqual(len(c), 3)

        result = cmds.count()
        self.assertEqual(result, 3)

        ShellContext.current_path = Path('/')

        result = cmds.count(resource='foo')
        self.assertEqual(result, 3)

        ShellContext.current_path = Path('/foo/%s' % uuid.uuid4())

        result = cmds.count()
        self.assertEqual(result, None)

    @mock.patch('contrail_api_cli.utils.ResourceBase.session')
    @mock.patch('contrail_api_cli.commands.utils.continue_prompt')
    def test_rm(self, mock_continue_prompt, mock_session):
        mock_session.configure_mock(base_url=BASE)
        ShellContext.current_path = Path('/')
        t = 'foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f'
        mock_session.delete.return_value = True
        cmds.rm(resource=t, force=True)
        mock_session.delete.assert_has_calls([
            mock.call(BASE + '/foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f')
        ])
        self.assertFalse(mock_continue_prompt.called)

    @mock.patch('contrail_api_cli.utils.ResourceBase.session')
    @mock.patch('contrail_api_cli.commands.utils.continue_prompt')
    def test_rm_noconfirm(self, mock_continue_prompt, mock_session):
        ShellContext.current_path = Path('/')
        mock_continue_prompt.return_value = False
        t = 'foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f'
        cmds.rm(resource=t)
        self.assertFalse(mock_session.delete.called)

    @mock.patch('contrail_api_cli.utils.ResourceBase.session')
    @mock.patch('contrail_api_cli.commands.utils.continue_prompt')
    def test_rm_recursive(self, mock_continue_prompt, mock_session):
        ShellContext.current_path = Path('/')
        t = 'foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f'
        mock_continue_prompt.return_value = True
        mock_session.configure_mock(base_url=BASE)
        mock_session.get.side_effect = [
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
        cmds.rm(resource=t, recursive=True)
        expected_calls = [
            mock.call.get(BASE + '/foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f'),
            mock.call.get(BASE + '/bar/22916187-5b6f-40f1-b7b6-fc6fe9f23bce'),
            mock.call.get(BASE + '/foobar/1050223f-a230-4ed6-96f1-c332700c5e01'),
            mock.call.get(BASE + '/bar/776bdf88-6283-4c4b-9392-93a857807307'),
            mock.call.delete(BASE + '/bar/776bdf88-6283-4c4b-9392-93a857807307'),
            mock.call.delete(BASE + '/foobar/1050223f-a230-4ed6-96f1-c332700c5e01'),
            mock.call.delete(BASE + '/bar/22916187-5b6f-40f1-b7b6-fc6fe9f23bce'),
            mock.call.delete(BASE + '/foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f')
        ]
        self.assertEqual(mock_session.mock_calls, expected_calls)


if __name__ == '__main__':
    unittest.main()
