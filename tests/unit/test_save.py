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
import shutil

import boto3

try:
    import mock
except ImportError:
    import unittest.mock as mock

import placebo


kp_result_foo = {
    "KeyPairs": [
        {
            "KeyName": "foo",
            "KeyFingerprint": "ad:08:8a:b3:13:ea:6c:20:fa"
        }
    ]
}

kp_result_bar = {
    "KeyPairs": [
        {
            "KeyName": "bar",
            "KeyFingerprint": ":27:21:b9:ce:b5:5a:a2:a3:bc"
        }
    ]
}

addresses_result_one = {
    "Addresses": [
        {
            "InstanceId": "",
            "PublicIp": "192.168.0.1",
            "Domain": "standard"
        }
    ]
}


class TestPlacebo(unittest.TestCase):

    def setUp(self):
        self.environ = {}
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()
        credential_path = os.path.join(os.path.dirname(__file__), 'cfg',
                                       'aws_credentials')
        self.environ['AWS_SHARED_CREDENTIALS_FILE'] = credential_path
        self.data_path = os.path.join(os.path.dirname(__file__), 'responses')
        self.data_path = os.path.join(self.data_path, 'tests')
        if os.path.exists(self.data_path):
            shutil.rmtree(self.data_path)
        os.mkdir(self.data_path)
        self.session = boto3.Session(profile_name='foobar',
                                     region_name='us-west-2')
        self.pill = placebo.attach(self.session, self.data_path)

    def tearDown(self):
        if os.path.exists(self.data_path):
            shutil.rmtree(self.data_path)

    def test_ec2(self):
        self.assertEqual(len(os.listdir(self.data_path)), 0)
        self.pill.save_response(
            'ec2', 'DescribeAddresses',
            '572586b59ad20af121cc892001c61eeef275d7184f3b28d17e35331536fabdc7',
            addresses_result_one
        )
        self.assertEqual(len(os.listdir(self.data_path)), 1)
        self.pill.playback()
        ec2_client = self.session.client('ec2')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '192.168.0.1')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '192.168.0.1')

    # newer calls should overwrite older one's
    def test_ec2_multiple_responses(self):
        self.assertEqual(len(os.listdir(self.data_path)), 0)
        self.pill.save_response(
            'ec2', 'DescribeKeyPairs',
            '1ef2ff140613ecd853639efe0dfd5429f40823ffefed62386485b3ace20c9908',
            kp_result_foo
        )
        self.assertEqual(len(os.listdir(self.data_path)), 1)
        self.pill.save_response(
            'ec2', 'DescribeKeyPairs',
            '1ef2ff140613ecd853639efe0dfd5429f40823ffefed62386485b3ace20c9908',
            kp_result_bar
        )
        self.assertEqual(len(os.listdir(self.data_path)), 1)
        self.pill.playback()
        ec2_client = self.session.client('ec2')
        result = ec2_client.describe_key_pairs()
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'bar')

    def test_multiple_clients(self):
        self.assertEqual(len(os.listdir(self.data_path)), 0)
        params_hash = '572586b59ad20af121cc892001c61eeef275d7184f3b28d17e35331536fabdc7'
        self.pill.save_response(
            'ec2', 'DescribeAddresses', params_hash, addresses_result_one)
        self.pill.playback()
        ec2_client = self.session.client('ec2')
        iam_client = self.session.client('iam')
        result = ec2_client.describe_addresses()
        self.assertEqual(len(os.listdir(self.data_path)), 1)
