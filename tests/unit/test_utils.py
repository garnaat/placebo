import unittest
import os
import shutil

import boto3
import mock

from placebo.utils import placebo_session


class TestUtils(unittest.TestCase):

    def setUp(self):
        self.environ = {}
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()
        credential_path = os.path.join(os.path.dirname(__file__), 'cfg',
                                       'aws_credentials')
        self.environ['AWS_SHARED_CREDENTIALS_FILE'] = credential_path
        self.environ['PLACEBO_MODE'] = 'record'
        self.environ['PLACEBO_DIR'] = 'placebo_test_runs'
        self.session = boto3.Session(profile_name='foobar',
                                     region_name='us-west-2')

    @placebo_session
    def test_decorator(self, session):

        # Tear it up..
        PLACEBO_TEST_DIR = os.path.join(os.getcwd(), 'placebo_test_runs')
        prefix = 'TestUtils.test_decorator'
        record_dir = os.path.join(PLACEBO_TEST_DIR, prefix)
        self.assertTrue(os.path.exists(record_dir))

        # Tear it down..
        shutil.rmtree(PLACEBO_TEST_DIR)
