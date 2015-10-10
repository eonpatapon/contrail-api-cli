import unittest
try:
    import mock
except ImportError:
    import unittest.mock as mock

import contrail_api_cli.commands as cmds
from contrail_api_cli.utils import Path
from contrail_api_cli.client import BASE_URL


class TestCommands(unittest.TestCase):

    @mock.patch('contrail_api_cli.commands.APIClient.request')
    def test_home_ls(self, mock_request):
        p = Path()
        expected_home_resources = [
            Path("instance-ip"),
        ]

        mock_request.return_value = {
            "href": BASE_URL,
            "links": [
                {"link": {"href": BASE_URL + "/instance-ips",
                          "name": "instance-ip",
                          "rel": "collection"}},
                {"link": {"href": BASE_URL + "/instance-ip",
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
                {"href": BASE_URL + "/instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724",
                 "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724"},
                {"href": BASE_URL + "/instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a",
                 "uuid": "c2588045-d6fb-4f37-9f46-9451f653fb6a"}
            ]
        }
        expected_resources = [
            Path("instance-ip/ec1afeaa-8930-43b0-a60a-939f23a50724"),
            Path("instance-ip/c2588045-d6fb-4f37-9f46-9451f653fb6a"),
        ]
        result = cmds.ls(p)
        self.assertEqual(result, expected_resources)

if __name__ == "__main__":
    unittest.main()
