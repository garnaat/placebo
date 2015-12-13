# Copyright (c) 2015 Mitch Garnaat
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
import shutil

import boto3

import placebo


class TestPlacebo(unittest.TestCase):

    def setUp(self):
        self.data_path = os.path.join(os.path.dirname(__file__), 'responses')
        self.data_path = os.path.join(self.data_path, 'saved')
        self.session = boto3.Session()
        self.pill = placebo.attach(self.session, self.data_path)

    def tearDown(self):
        pass

    def test_describe_addresses(self):
        self.pill.playback()
        ec2_client = self.session.client('ec2')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '52.53.54.55')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '53.54.55.56')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '52.53.54.55')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '53.54.55.56')

    def test_describe_key_pairs(self):
        self.pill.playback()
        ec2_client = self.session.client('ec2')
        result = ec2_client.describe_key_pairs()
        self.assertEqual(len(result['KeyPairs']), 2)
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'FooBar')
        self.assertEqual(result['KeyPairs'][1]['KeyName'], 'FieBaz')
