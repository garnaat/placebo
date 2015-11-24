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

import boto3

import placebo

kp_result_one = {
    "KeyPairs": [
        {
            "KeyName": "foo",
            "KeyFingerprint": "ad:08:8a:b3:13:ea:6c:20:fa"
        }
    ]
}

kp_result_two = {
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

    def test_ec2(self):
        session = boto3.Session()
        ec2_client = session.client('ec2')
        placebo.mock_client(ec2_client)
        ec2_client.mock.add_response(
            'DescribeAddresses', addresses_result_one)
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '192.168.0.1')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '192.168.0.1')

    def test_ec2_multiple_responses(self):
        session = boto3.Session()
        ec2_client = session.client('ec2')
        placebo.mock_client(ec2_client)
        ec2_client.mock.add_response(
            'DescribeKeyPairs', kp_result_one)
        ec2_client.mock.add_response(
            'DescribeKeyPairs', kp_result_two)
        result = ec2_client.describe_key_pairs()
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'foo')
        result = ec2_client.describe_key_pairs()
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'bar')
        result = ec2_client.describe_key_pairs()
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'bar')
