import unittest
try:
    import mock
except ImportError:
    import unittest.mock as mock

import contrail_api_cli.commands as cmds
from contrail_api_cli.utils import Path
from contrail_api_cli.client import APIClient


class TestCommands(unittest.TestCase):

    @mock.patch('contrail_api_cli.commands.APIClient.request')
    def test_home_ls(self, mock_request):
        p = Path()
        expected_home_resources = [
            Path("instance-ip"),
        ]

        mock_request.return_value = {
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

    @mock.patch('contrail_api_cli.commands.APIClient.request')
    def test_resources_ls(self, mock_request):
        p = Path("instance-ip")
        mock_request.return_value = {
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

    @mock.patch('contrail_api_cli.commands.APIClient.request')
    @mock.patch('contrail_api_cli.commands.Ls.colorize')
    def test_resource_ls(self, mock_colorize, mock_request):
        p = Path('foo')
        mock_request.return_value = {
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

if __name__ == "__main__":
    unittest.main()
