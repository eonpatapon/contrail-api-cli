# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unittest
try:
    import mock
except ImportError:
    import unittest.mock as mock

import contrail_api_cli.schema as schema
from contrail_api_cli.context import Context
from contrail_api_cli.resource import Resource, LinkedResources, LinkType, Collection

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

    @mock.patch('contrail_api_cli.resource.Context.session')
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

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_schema_refs(self, mock_session):
        mock_session.get_json.return_value = {
            "virtual-machine-interface": {
                "href": BASE + "/virtual-machine-interface/ec1afeaa-8930-43b0-a60a-939f23a50724",
                "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724",
                "attr": None,
                "fq_name": [
                    "virtual-machine-interface",
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

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_schema_children(self, mock_session):
        mock_session.get_json.side_effect = [
            {
                "project": {
                    "href": BASE + "/project/ec1afeaa-8930-43b0-a60a-939f23a50724",
                    "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724",
                    "attr": None,
                    "fq_name": [
                        "project",
                        "ec1afeaa-8930-43b0-a60a-939f23a50724"
                    ],
                    "virtual_networks": [
                        {
                            "href": BASE + "/virtual-network/15315402-8a21-4116-aeaa-b6a77dceb191",
                            "uuid": "15315402-8a21-4116-aeaa-b6a77dceb191",
                            "to": [
                                "virtual-network",
                                "15315402-8a21-4116-aeaa-b6a77dceb191"
                            ]
                        }
                    ]
                }
            },
            {
                'virtual-network': []
            }
        ]
        vmi = Resource('project', uuid='ec1afeaa-8930-43b0-a60a-939f23a50724', fetch=True)
        self.assertEqual(len(vmi.children.virtual_network), 1)
        self.assertEqual(type(vmi.children.virtual_network), Collection)
        self.assertTrue(vmi.children.virtual_network.type, 'virtual-network')
        self.assertTrue(vmi.children.virtual_network.parent_uuid, vmi.uuid)
        vmi.children.virtual_network.fetch()
        mock_session.get_json.assert_called_with(vmi.children.virtual_network.href, parent_id=vmi.uuid)

    @mock.patch('contrail_api_cli.resource.Context.session')
    def test_schema_back_refs(self, mock_session):
        mock_session.get_json.side_effect = [
            {
                "virtual-network": {
                    "href": BASE + "/virtual-network/ec1afeaa-8930-43b0-a60a-939f23a50724",
                    "uuid": "ec1afeaa-8930-43b0-a60a-939f23a50724",
                    "attr": None,
                    "fq_name": [
                        "virtual-network",
                        "ec1afeaa-8930-43b0-a60a-939f23a50724"
                    ],
                    "instance_ip_back_refs": [
                        {
                            "href": BASE + "/instance-ip/15315402-8a21-4116-aeaa-b6a77dceb191",
                            "uuid": "15315402-8a21-4116-aeaa-b6a77dceb191",
                            "to": [
                                "instance-ip",
                                "15315402-8a21-4116-aeaa-b6a77dceb191"
                            ]
                        }
                    ]
                }
            },
            {
                'instance-ip': []
            }
        ]
        vn = Resource('virtual-network', uuid='ec1afeaa-8930-43b0-a60a-939f23a50724', fetch=True)
        self.assertEqual(len(vn.back_refs.instance_ip), 1)
        self.assertEqual(type(vn.back_refs.instance_ip), Collection)
        self.assertTrue(vn.back_refs.instance_ip.type, 'instance-ip')
        self.assertTrue(vn.back_refs.instance_ip.back_refs_uuid, vn.uuid)
        vn.back_refs.instance_ip.fetch()
        mock_session.get_json.assert_called_with(vn.back_refs.instance_ip.href, back_ref_id=vn.uuid)

    def test_require_schema(self):

        @schema.require_schema(version='> 3')
        def test_gt():
            pass

        @schema.require_schema(version='< 3')
        def test_lt():
            pass

        @schema.require_schema(version='2.21')
        def test_eq():
            pass

        with self.assertRaises(schema.SchemaError):
            test_gt()

        test_lt()
        test_eq()


if __name__ == "__main__":
    unittest.main()
