from __future__ import unicode_literals
import unittest
try:
    import mock
except ImportError:
    import unittest.mock as mock

from contrail_api_cli.context import Context
from contrail_api_cli.schema import DummySchema, DummyResourceSchema


class CLITest(unittest.TestCase):

    @mock.patch('contrail_api_cli.resource.Context.session')
    def setUp(self, mock_session):
        self.maxDiff = None
        self.BASE = "http://localhost:8082"
        mock_session.configure_mock(base_url=self.BASE)
        mock_session.get_json.return_value = {
            "href": self.BASE,
            "links": [
                {"link": {"href": self.BASE + "/foos",
                          "name": "foo",
                          "rel": "collection"}},
                {"link": {"href": self.BASE + "/bars",
                          "name": "bar",
                          "rel": "collection"}},
                {"link": {"href": self.BASE + "/foobars",
                          "name": "foobar",
                          "rel": "collection"}}
            ]
        }
        DummyResourceSchema()
        Context().schema = DummySchema()

    def tearDown(self):
        Context().schema = None
