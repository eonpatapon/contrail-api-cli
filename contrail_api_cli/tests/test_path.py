# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unittest
from uuid import uuid4

from contrail_api_cli.utils import Path
from contrail_api_cli.exceptions import AbsPathRequired


class TestPath(unittest.TestCase):

    def test_cd(self):
        p = Path("/")
        p = p / "foo" / "bar"
        self.assertEqual(str(p), "/foo/bar")
        p = p / ".." / "foo"
        self.assertEqual(str(p), "/foo/foo")

    def test_resource(self):
        p = Path("/foo/%s" % str(uuid4()))
        self.assertTrue(p.is_resource)
        p = Path("/foo/bar")
        self.assertTrue(p.is_resource)
        p = Path("/")
        self.assertFalse(p.is_resource)
        p = Path("/75963ada-2c70-4eeb-8daf-f24ce920ff7b")
        self.assertFalse(p.is_resource)
        p = Path("foo/bar")
        with self.assertRaises(AbsPathRequired):
            p.is_resource

    def test_collection(self):
        p = Path("/foo")
        self.assertTrue(p.is_collection)
        p = Path("/foo/bar")
        self.assertFalse(p.is_collection)
        p = Path("/")
        self.assertTrue(p.is_collection)
        p = Path("foo/bar")
        with self.assertRaises(AbsPathRequired):
            p.is_collection

    def test_uuid(self):
        p = Path("/foo/%s" % str(uuid4()))
        self.assertTrue(p.is_uuid)
        p = Path("/foo/bar")
        self.assertFalse(p.is_uuid)

    def test_fq_name(self):
        p = Path("/foo/%s" % str(uuid4()))
        self.assertFalse(p.is_fq_name)
        p = Path("/foo/bar")
        self.assertTrue(p.is_fq_name)

    def test_root(self):
        p = Path("/")
        self.assertTrue(p.is_root)
        p = Path("/foo")
        self.assertFalse(p.is_root)

    def test_base(self):
        p = Path("/foo")
        self.assertEqual(p.base, "foo")
        p = Path("/foo/%s" % uuid4())
        self.assertEqual(p.base, "foo")
        p = Path("/")
        self.assertEqual(p.base, "")

    def test_unicode(self):
        p = Path("/éà")
        self.assertEqual(p.base, "??")


if __name__ == "__main__":
    unittest.main()
