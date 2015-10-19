import unittest
import uuid
try:
    import mock
except ImportError:
    import unittest.mock as mock

import contrail_api_cli.commands as cmds
from contrail_api_cli.utils import Path
from contrail_api_cli.client import APIClient


class TestCommands(unittest.TestCase):

    @mock.patch('contrail_api_cli.commands.APIClient.get')
    def test_home_ls(self, mock_get):
        p = Path()
        expected_home_resources = [
            Path("instance-ip"),
        ]

        mock_get.return_value = {
            "href": APIClient.base_url,
            "links": [
                {"link": {"href": Path("instance-ip"),
                          "name": "instance-ip",
                          "rel": "collection"}},
                {"link": {"href": Path("instance-ip"),
                          "name": "instance-ip",
                          "rel": "resource-base"}}
            ]
        }
        result = cmds.ls(p)
        self.assertEqual(result, expected_home_resources)

    @mock.patch('contrail_api_cli.commands.APIClient.get')
    def test_resources_ls(self, mock_get):
        p = Path("instance-ip")
        mock_get.return_value = {
            "instance-ips": [
                {"href": Path("instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724"),
                 "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724"},
                {"href": Path("instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a"),
                 "uuid": "c2588045-d6fb-4f37-9f46-9451f653fb6a"}
            ]
        }
        expected_resources = [
            Path("instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724"),
            Path("instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a"),
        ]
        result = cmds.ls(p)
        self.assertEqual(result, expected_resources)

    @mock.patch('contrail_api_cli.commands.APIClient.get')
    @mock.patch('contrail_api_cli.commands.Ls.colorize')
    def test_resource_ls(self, mock_colorize, mock_get):
        p = Path('foo')
        mock_get.return_value = {
            "foo": {
                "href": Path("/foo/ec1afeaa-8930-43b0-a60a-939f23a50724"),
                "attr": None,
                "fq_name": [
                    "foo",
                    "ec1afeaa-8930-43b0-a60a-939f23a50724"
                ],
                "bar_refs": [
                    {
                        "href": Path("/bar/ec1afeaa-8930-43b0-a60a-939f23a50724"),
                        "to": [
                            "bar",
                            "ec1afeaa-8930-43b0-a60a-939f23a50724"
                        ]
                    }
                ]
            }
        }
        mock_colorize.side_effect = lambda d: d
        expected_resource = {
            "href": Path("ec1afeaa-8930-43b0-a60a-939f23a50724"),
            "fq_name": "foo:ec1afeaa-8930-43b0-a60a-939f23a50724",
            "bar_refs": [
                {
                    "href": Path("bar/ec1afeaa-8930-43b0-a60a-939f23a50724"),
                    "to": "bar:ec1afeaa-8930-43b0-a60a-939f23a50724"
                }
            ]
        }
        result = cmds.ls(p, 'ec1afeaa-8930-43b0-a60a-939f23a50724')
        self.assertEqual(result, expected_resource)

    @mock.patch('contrail_api_cli.commands.APIClient.get')
    def test_count(self, mock_get):
        p = Path('foo')
        mock_get.return_value = {
            'foos': {
                'count': 3
            }
        }
        result = cmds.count(p)
        self.assertEqual(result, 3)

        p = Path()
        result = cmds.count(p, 'foo')
        self.assertEqual(result, 3)

        p = Path('foo/%s' % uuid.uuid4())
        result = cmds.count(p)
        self.assertEqual(result, None)

    @mock.patch('contrail_api_cli.commands.APIClient.delete')
    @mock.patch('contrail_api_cli.commands.utils.continue_prompt')
    def test_rm(self, mock_continue_prompt, mock_delete):
        p = Path()
        t = Path("foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f")
        mock_continue_prompt.return_value = True
        mock_delete.return_value = True
        cmds.rm(p, t)
        mock_delete.assert_has_calls([mock.call(Path("foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f"))])

    @mock.patch('contrail_api_cli.commands.APIClient.get')
    @mock.patch('contrail_api_cli.commands.APIClient.delete')
    @mock.patch('contrail_api_cli.commands.utils.continue_prompt')
    def test_rm_recursive(self, mock_continue_prompt, mock_delete, mock_get):
        p = Path()
        t = Path("foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f")
        mock_continue_prompt.return_value = True
        mock_get.side_effect = [
            {
                'foo': {
                    'href': Path("foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f"),
                    'bar_back_refs': [
                        {
                            "href": Path("bar/22916187-5b6f-40f1-b7b6-fc6fe9f23bce")
                        },
                        {
                            "href": Path("bar/776bdf88-6283-4c4b-9392-93a857807307")
                        }
                    ]
                }
            },
            {
                'bar': {
                    'href': Path("bar/22916187-5b6f-40f1-b7b6-fc6fe9f23bce"),
                    'foobar_back_refs': [
                        {
                            'href': Path("foobar/1050223f-a230-4ed6-96f1-c332700c5e01")
                        }
                    ]
                }
            },
            {
                'foobar': {
                    'href': Path("foobar/1050223f-a230-4ed6-96f1-c332700c5e01")
                }
            },
            {
                'bar': {
                    'href': Path("bar/776bdf88-6283-4c4b-9392-93a857807307")
                }
            }
        ]
        mock_delete.return_value = True
        cmds.rm(p, t, "-r")
        mock_delete.assert_has_calls([
            mock.call(Path("bar/776bdf88-6283-4c4b-9392-93a857807307")),
            mock.call(Path("foobar/1050223f-a230-4ed6-96f1-c332700c5e01")),
            mock.call(Path("bar/22916187-5b6f-40f1-b7b6-fc6fe9f23bce")),
            mock.call(Path("foo/6b6a7f47-807e-4c39-8ac6-3adcf2f5498f"))
        ])


if __name__ == "__main__":
    unittest.main()
