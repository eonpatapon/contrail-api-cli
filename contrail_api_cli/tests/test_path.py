import unittest
from uuid import uuid4

from contrail_api_cli.utils import Path


class TestPath(unittest.TestCase):

    def test_init(self):
        p = Path()
        self.assertEqual(str(p), "/")
        p = Path("foo")
        self.assertEqual(str(p), "/foo")
        p = Path("foo", "bar")
        self.assertEqual(str(p), "/foo/bar")
        p = Path("foo/bar")
        self.assertEqual(str(p), "/foo/bar")

    def test_cd(self):
        p = Path()
        p.cd("foo")
        self.assertEqual(str(p), "/foo")
        p.cd("foo/bar")
        self.assertEqual(str(p), "/foo/foo/bar")
        p.cd("/foo/bar")
        self.assertEqual(str(p), "/foo/bar")
        p.cd("..")
        self.assertEqual(str(p), "/foo")
        p.cd(".")
        self.assertEqual(str(p), "/foo")
        p.cd()
        self.assertEqual(str(p), "/")

    def test_relative(self):
        p1 = Path()
        p2 = Path("foo/bar")
        p2_rel = p2.relative(p1)
        self.assertEqual(str(p2_rel), "foo/bar")
        self.assertFalse(p2_rel.absolute)
        p1 = Path("foo")
        p2 = Path("foo/bar")
        p2_rel = p2.relative(p1)
        self.assertEqual(str(p2_rel), "bar")
        self.assertFalse(p2_rel.absolute)
        p1 = Path("bar")
        p2 = Path("foo/bar")
        p2_rel = p2.relative(p1)
        self.assertEqual(str(p2_rel), "/foo/bar")
        self.assertTrue(p2_rel.absolute)

    def test_resource(self):
        p = Path("foo/%s" % str(uuid4()))
        self.assertTrue(p.is_resource)
        p = Path("foo/bar")
        self.assertFalse(p.is_resource)
        p = Path()
        self.assertFalse(p.is_resource)

    def test_root(self):
        p = Path()
        self.assertTrue(p.is_root)
        p = Path("foo")
        self.assertFalse(p.is_root)

    def test_resource_name(self):
        p = Path("foo")
        self.assertEqual(p.resource_name, "foo")
        p = Path("foo/%s" % uuid4())
        self.assertEqual(p.resource_name, "foo")
        p = Path()
        self.assertEqual(p.resource_name, None)


if __name__ == "__main__":
    unittest.main()
