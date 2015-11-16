import unittest
from uuid import uuid4

from contrail_api_cli.utils import Path


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
        self.assertFalse(p.is_resource)
        p = Path("/")
        self.assertFalse(p.is_resource)

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


if __name__ == "__main__":
    unittest.main()
