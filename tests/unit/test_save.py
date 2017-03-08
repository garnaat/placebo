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
import mock

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

ecs_cluster = {
    "cluster": [
        {
            "activeServicesCount": 0,
            "clusterArn": "arn:aws:ecs:us-east-1:394828193847:cluster/My-cluster",
            "clusterName": "My-cluster",
            "pendingTasksCount": 0,
            "registeredContainerInstancesCount": 0,
            "runningTasksCount": 0,
            "status": "ACTIVE"
        }
    ],
    "failures": []
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
            'ec2', 'DescribeAddresses', addresses_result_one)
        self.assertEqual(len(os.listdir(self.data_path)), 1)
        self.pill.playback()
        ec2_client = self.session.client('ec2')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '192.168.0.1')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '192.168.0.1')

    def test_ec2_multiple_responses(self):
        self.assertEqual(len(os.listdir(self.data_path)), 0)
        self.pill.save_response(
            'ec2', 'DescribeKeyPairs', kp_result_one)
        self.assertEqual(len(os.listdir(self.data_path)), 1)
        self.pill.save_response(
            'ec2', 'DescribeKeyPairs', kp_result_two)
        self.assertEqual(len(os.listdir(self.data_path)), 2)
        self.pill.playback()
        ec2_client = self.session.client('ec2')
        result = ec2_client.describe_key_pairs()
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'foo')
        result = ec2_client.describe_key_pairs()
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'bar')
        result = ec2_client.describe_key_pairs()
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'foo')

    def test_multiple_clients(self):
        self.assertEqual(len(os.listdir(self.data_path)), 0)
        self.pill.save_response(
            'ec2', 'DescribeAddresses', addresses_result_one)
        self.pill.playback()
        ec2_client = self.session.client('ec2')
        iam_client = self.session.client('iam')
        result = ec2_client.describe_addresses()
        self.assertEqual(len(os.listdir(self.data_path)), 1)

    def test_masking_arn(self):
        """Verify only the account number of the ARN gets replaced."""
        self.pill.mask_account_number = True
        self.assertEqual(len(os.listdir(self.data_path)), 0)
        self.pill.save_response(
            'ecs', 'DescribeClusters', ecs_cluster)
        self.assertEqual(len(os.listdir(self.data_path)), 1)
        self.pill.playback()
        ecs_client = self.session.client('ecs')
        response = ecs_client.describe_clusters(
            clusters=[
                'My-cluster'
            ])
        expected_response = {
            "cluster": [
                {
                    "activeServicesCount": 0,
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/My-cluster",
                    "clusterName": "My-cluster",
                    "pendingTasksCount": 0,
                    "registeredContainerInstancesCount": 0,
                    "runningTasksCount": 0,
                    "status": "ACTIVE"
                }
            ],
            "failures": []
        }
        self.assertEqual(response, expected_response)
