# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unittest

import contrail_api_cli.schema as schema


class TestSchema(unittest.TestCase):

    def test_load_non_existing_version(self):
        non_existing_version = "0"
        with self.assertRaises(schema.SchemaVersionNotAvailable):
            schema.create_schema_from_version(non_existing_version)

    def test_create_all_schema_versions(self):
        for v in schema.list_available_schema_version():
            schema.create_schema_from_version(v)

    def test_is_child(self):
        s = schema.create_schema_from_version("1.10")
        vn_res = s.resource("virtual-network")
        self.assertTrue(vn_res.is_child("routing-instance"))
        self.assertTrue(vn_res.is_child("routing_instance"))
        self.assertTrue(vn_res.is_child("routing_instances"))
        self.assertTrue(vn_res.is_child("routing-instances"))
        self.assertFalse(vn_res.is_child("foo"))

if __name__ == "__main__":
    unittest.main()
