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

import placebo


class TestPlacebo(unittest.TestCase):

    def setUp(self):
        self.environ = {}
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()
        credential_path = os.path.join(os.path.dirname(__file__), 'cfg',
                                       'aws_credentials')
        self.environ['AWS_SHARED_CREDENTIALS_FILE'] = credential_path
        self.data_path = os.path.join(os.path.dirname(__file__), 'responses')
        self.data_path = os.path.join(self.data_path, 'saved')
        self.session = boto3.Session(profile_name='foobar',
                                     region_name='us-west-2')
        self.pill = placebo.attach(self.session, self.data_path)

    def tearDown(self):
        pass

    def test_describe_addresses(self):
        self.pill.playback()
        ec2_client = self.session.client('ec2')
        result = ec2_client.describe_addresses()
        self.assertEqual(result['Addresses'][0]['PublicIp'], '52.53.54.55')

    def test_describe_key_pairs(self):
        self.pill.playback()
        ec2_client = self.session.client('ec2')
        result = ec2_client.describe_key_pairs()
        self.assertEqual(len(result['KeyPairs']), 2)
        self.assertEqual(result['KeyPairs'][0]['KeyName'], 'FooBar')
        self.assertEqual(result['KeyPairs'][1]['KeyName'], 'FieBaz')

    def test_describe_unordered(self):
        self.pill.playback()
        iam = self.session.client('iam')

        resp1 = iam.get_policy(PolicyArn='arn:aws:iam::aws:policy/AWSLambdaFullAccess')
        resp2 = iam.get_policy(PolicyArn='arn:aws:iam::aws:policy/AmazonEC2FullAccess')

        self.assertNotEqual(resp1['Policy']['PolicyName'], resp2['Policy']['PolicyName'])

    def test_prefix_new_file_path(self):
        self.pill.prefix = 'foo'
        service = 'ec2'
        operation = 'DescribeAddresses'
        params_hash = '6b1fd414173035b6f7f70aee6c4aedafd78910bd8632d9f0211057e5fd90bef4'
        filename = '{0}.{1}.{2}.{3}_1.json'.format(self.pill.prefix, service,
                                               operation, params_hash)
        target = os.path.join(self.data_path, filename)
        self.assertEqual(self.pill.get_new_file_path(service, operation, params_hash, 1),
                         target)

    def test_prefix_next_file_path(self):
        self.pill.prefix = 'foo'
        service = 'ec2'
        operation = 'DescribeAddresses'
        params_hash = '6b1fd414173035b6f7f70aee6c4aedafd78910bd8632d9f0211057e5fd90bef4'
        filename = '{0}.{1}.{2}.{3}_1.json'.format(self.pill.prefix, service,
                                               operation, params_hash)
        target = os.path.join(self.data_path, filename)
        (file_path, _) = self.pill.get_next_file_path(service, operation, params_hash)
        self.assertEqual(file_path, target)
