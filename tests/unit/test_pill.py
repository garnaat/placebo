# Copyright (c) 2015-2019 Mitch Garnaat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import os

import boto3

try:
    import mock
except ImportError:
    import unittest.mock as mock

import placebo.pill


class TestPill(unittest.TestCase):

    def setUp(self):
        self.environ = {}
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()
        credential_path = os.path.join(os.path.dirname(__file__), 'cfg',
                                       'aws_credentials')
        self.environ['AWS_SHARED_CREDENTIALS_FILE'] = credential_path
        self.data_path = os.path.join(os.path.dirname(__file__), 'responses')
        self.data_path = os.path.join(self.data_path, 'tests')
        self.session = boto3.Session(profile_name='foobar',
                                     region_name='us-west-2')
        self.pill = placebo.attach(self.session, self.data_path)

    def tearDown(self):
        pass

    def test_record(self):
        self.assertEqual(self.pill.mode, None)
        self.pill.record()
        self.assertEqual(self.pill.mode, 'record')
        self.assertEqual(
            self.pill.events,
            {
                'before-call.*.*': 'placebo-record-mode-before-call-_record_params',
                'after-call.*.*': 'placebo-record-mode-after-call-_record_data'
            })
        self.pill.stop()
        self.assertEqual(self.pill.mode, None)
        self.assertEqual(self.pill.events, {})
        self.pill.record('ec2')
        self.pill.record('iam', 'ListUsers')
        self.assertEqual(self.pill.mode, 'record')
        self.assertEqual(
            self.pill.events,
            {
                'after-call.ec2.*':           'placebo-record-mode-after-call-_record_data',
                'after-call.iam.ListUsers':   'placebo-record-mode-after-call-_record_data',
                'before-call.ec2.*':          'placebo-record-mode-before-call-_record_params',
                'before-call.iam.ListUsers':  'placebo-record-mode-before-call-_record_params'
            }
        )
        self.pill.stop()
        self.assertEqual(self.pill.mode, None)
        self.assertEqual(self.pill.events, {})

    def test_playback(self):
        self.pill.playback()
        self.assertEqual(self.pill.mode, 'playback')
        self.assertDictEqual(self.pill.events, {'before-call.*.*': 'placebo-playback-mode-before-call-_mock_request'})
        self.pill.stop()
        self.assertEqual(self.pill.events, {})

    def test_clients(self):
        ec2 = self.session.client('ec2')
        iam = self.session.client('iam')
        self.assertEqual(len(self.pill.clients), 2)
        self.assertTrue(ec2 in self.pill.clients)
        self.assertTrue(iam in self.pill.clients)
        session = boto3.Session(profile_name='foobar',
                                region_name='us-west-2')
        new_ec2 = session.client('ec2')
        self.assertEqual(len(self.pill.clients), 2)
        self.assertFalse(new_ec2 in self.pill.clients)
