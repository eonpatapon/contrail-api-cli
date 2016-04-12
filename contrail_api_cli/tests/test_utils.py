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

    def test_set_std_printo(self):
        FAKE_STRING_NEW_LINE = b"fake string\n"
        FAKE_STRING_NO_NEW_LINE = "fake string"
        orig_stdout = sys.stdout
        orig_stderr = sys.stdout
        fake_stdout = io.BytesIO()
        fake_stderr = io.BytesIO()
        sys.stdout = fake_stdout
        sys.stderr = fake_stderr

        def clear_buffers():
            fake_stdout.truncate(0)
            fake_stdout.seek(0)
            fake_stderr.truncate(0)
            fake_stderr.seek(0)

        utils.printo(FAKE_STRING_NO_NEW_LINE)
        self.assertEqual(fake_stdout.getvalue(), FAKE_STRING_NEW_LINE)
        self.assertEqual(fake_stderr.getvalue(), b'')
        clear_buffers()

        utils.printo(FAKE_STRING_NO_NEW_LINE, std_type='stdout')
        self.assertEqual(fake_stdout.getvalue(), FAKE_STRING_NEW_LINE)
        self.assertEqual(fake_stderr.getvalue(), b'')
        clear_buffers()

        utils.printo(FAKE_STRING_NO_NEW_LINE, std_type='stderr')
        self.assertEqual(fake_stdout.getvalue(), b'')
        self.assertEqual(fake_stderr.getvalue(), FAKE_STRING_NEW_LINE)
        clear_buffers()

        utils.printo(FAKE_STRING_NO_NEW_LINE, std_type='fake_std')
        self.assertEqual(fake_stdout.getvalue(), FAKE_STRING_NEW_LINE)
        self.assertEqual(fake_stderr.getvalue(), b'')
        clear_buffers()

        sys.stdout = orig_stdout
        sys.stderr = orig_stderr

    def test_paralel_map(self):
        lst = [1, 2, 3, 4, 5]
        res = utils.parallel_map(lambda x: x * 2, lst)
        expected = list(map(lambda x: x * 2, lst))
        self.assertEqual(res, expected)

        res = utils.parallel_map(lambda x: x * 2, lst, workers=2)
        expected = list(map(lambda x: x * 2, lst))
        self.assertEqual(res, expected)


if __name__ == '__main__':
    unittest.main()
