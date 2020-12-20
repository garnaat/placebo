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
import json
import os
import shutil
import unittest
from pathlib import Path

import moto
from moto.iam import mock_iam

import boto3
import placebo


class TestPaginateRecorder(unittest.TestCase):
    test_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "test",
            "Effect": "Allow",
            "Action": "*",
            "Resource": "*"
        }
    ]
}


    def setUp(self):
        self.data_path = os.path.join(os.path.dirname(__file__), 'responses')
        self.data_path = os.path.join(self.data_path, 'paginate')
        if not os.path.exists(self.data_path):
            os.mkdir(self.data_path)

        self.num_policies = 150

        #self.mock_iam = moto.mock_iam()
        with mock_iam():
            self.session = boto3.session.Session(region_name='us-east-1')
            self.pill = placebo.attach(self.session, data_path=self.data_path)
            self.pill.stop()
            self.iam = self.session.client('iam')
            self.setup_policies()

    def setup_policies(self):
        # Create a bunch of IAM policies with moto
        for i in range(self.num_policies):
            self.iam.create_policy(PolicyName='test-{}'.format(i), PolicyDocument=json.dumps(self.test_policy))


        # Run through them once to record them on disk
        self.pill.record()

        paginator = self.iam.get_paginator('list_policies')
        list(paginator.paginate(Scope='Local'))  # make a list to ensure all pages get recorded

        self.policy_check_arn = "arn:aws:iam::123456789012:policy/test-0"
        resp = self.iam.get_policy(PolicyArn=self.policy_check_arn)
        self.iam.get_policy_version(PolicyArn=self.policy_check_arn, VersionId=resp['Policy']['DefaultVersionId'])

        self.pill.stop()

    def tearDown(self):
        if os.path.exists(self.data_path):
            shutil.rmtree(self.data_path)
        self.pill.stop()

    def test_number_of_paginated_files_created(self):
            p = Path(self.data_path)
            self.assertEqual(len(list(p.glob('iam.ListPolicies.*.json'))), 2)

            files = list(p.glob('iam.ListPolicies.*_1.json'))
            self.assertEqual(len(list(files)), 1)

            files = list(p.glob('iam.ListPolicies.*_100.json'))
            self.assertEqual(len(list(files)), 1)

    def test_number_of_policies_created(self):
            p = Path(self.data_path)
            count = 0
            for file in p.glob("iam.ListPolicies.*.json"):
                with open(file, 'r') as f:
                    result = json.load(f)
                    count += len(result['data']['Policies'])

            self.assertEqual(count, self.num_policies)

    def test_playback_policy_count(self):
        self.pill.playback()

        paginator = self.iam.get_paginator('list_policies')
        results = paginator.paginate(Scope='Local')

        policies = results.build_full_result()['Policies']
        self.assertEqual(len(policies), self.num_policies)


    def test_playback_policy_content(self):
        self.pill.playback()
        resp = self.iam.get_policy(PolicyArn=self.policy_check_arn)
        resp = self.iam.get_policy_version(PolicyArn=self.policy_check_arn, VersionId=resp['Policy']['DefaultVersionId'])
        self.assertDictEqual(resp['PolicyVersion']['Document'], self.test_policy)
