# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unittest
try:
    import mock
except ImportError:
    import unittest.mock as mock

import contrail_api_cli.schema as schema
from contrail_api_cli.context import Context
from contrail_api_cli.resource import Resource, LinkedResources, LinkType

BASE = "http://localhost:8082"


class TestSchema(unittest.TestCase):

    def test_load_non_existing_version(self):
        non_existing_version = "0"
        with self.assertRaises(schema.SchemaVersionNotAvailable):
            schema.create_schema_from_version(non_existing_version)

    def test_create_all_schema_versions(self):
        for v in schema.list_available_schema_version():
            schema.create_schema_from_version(v)


class TestLinkResource(unittest.TestCase):

    def setUp(self):
        Context().schema = schema.create_schema_from_version('2.21')

    def tearDown(self):
        Context().schema = None

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_attr_transformations(self, mock_session):
        lr = LinkedResources(LinkType.REF,
                             Resource('virtual-machine-interface', fq_name='foo'))
        self.assertEqual(lr._type_to_attr('virtual-machine'), 'virtual_machine_refs')
        self.assertEqual(lr._type_to_attr('virtual_machine'), 'virtual_machine_refs')
        self.assertEqual(lr._attr_to_type('virtual_machine'), 'virtual-machine')
        self.assertEqual(lr._attr_to_type('virtual_machine_refs'), 'virtual-machine')
        self.assertEqual(lr._attr_to_type('virtual_machine_back_refs'), 'virtual-machine-back')

        lr = LinkedResources(LinkType.BACK_REF,
                             Resource('virtual-machine-interface', fq_name='foo'))
        self.assertEqual(lr._type_to_attr('virtual-machine'), 'virtual_machine_back_refs')
        self.assertEqual(lr._attr_to_type('virtual_machine_back_refs'), 'virtual-machine')
        self.assertEqual(lr._attr_to_type('virtual_machine_refs'), 'virtual-machine-refs')

        lr = LinkedResources(LinkType.CHILDREN,
                             Resource('virtual-machine-interface', fq_name='foo'))
        self.assertEqual(lr._type_to_attr('virtual-machine'), 'virtual_machines')
        self.assertEqual(lr._attr_to_type('virtual_machines'), 'virtual-machine')
        self.assertEqual(lr._attr_to_type('virtual_machine_refs'), 'virtual-machine-ref')

    @mock.patch('contrail_api_cli.resource.ResourceBase.session')
    def test_schema_refs(self, mock_session):
        mock_session.get_json.return_value = {
            "virtual-machine-interface": {
                "href": BASE + "/foo/ec1afeaa-8930-43b0-a60a-939f23a50724",
                "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724",
                "attr": None,
                "fq_name": [
                    "foo",
                    "ec1afeaa-8930-43b0-a60a-939f23a50724"
                ],
                "bar_refs": [1, 2, 3],
                "virtual_machine_refs": [
                    {
                        "href": BASE + "/virtual-machine/15315402-8a21-4116-aeaa-b6a77dceb191",
                        "uuid": "15315402-8a21-4116-aeaa-b6a77dceb191",
                        "to": [
                            "bar",
                            "15315402-8a21-4116-aeaa-b6a77dceb191"
                        ]
                    }
                ]
            }
        }
        vmi = Resource('virtual-machine-interface', uuid='ec1afeaa-8930-43b0-a60a-939f23a50724', fetch=True)
        self.assertEqual(len(vmi.refs.virtual_machine), 1)
        self.assertTrue(type(vmi.refs.virtual_machine[0]) == Resource)
        self.assertEqual(len(vmi.refs.bar), 0)
        self.assertEqual([r.uuid for r in vmi.refs], ['15315402-8a21-4116-aeaa-b6a77dceb191'])

if __name__ == "__main__":
    unittest.main()
