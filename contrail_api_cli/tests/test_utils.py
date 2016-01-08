# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unittest
import sys
import io

from contrail_api_cli import utils


class TestUtils(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    def test_printo(self):
        origout = sys.stdout
        tmpout = io.BytesIO()
        sys.stdout = tmpout
        utils.printo('é', encoding='ascii')
        utils.printo('é', encoding='utf-8')
        sys.stdout = origout
        self.assertEqual(tmpout.getvalue(), b'?\n\xc3\xa9\n')


if __name__ == '__main__':
    unittest.main()
