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

if __name__ == "__main__":
    unittest.main()
