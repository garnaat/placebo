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

import boto3
from moto import mock_iam
import placebo


class TestPagination(unittest.TestCase):
    test_policy = '''
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Deny",
            "Action": "*",
            "Resource": "*"
        }
    ]
}
'''

    def setUp(self):
        self.data_path = os.path.join(os.path.dirname(__file__), 'responses')
        self.data_path = os.path.join(self.data_path, 'paginate')
        if not os.path.exists(self.data_path):
            os.mkdir(self.data_path)

    def tearDown(self):
        if os.path.exists(self.data_path):
            shutil.rmtree(self.data_path)

    def test_my_model_save(self):
        with mock_iam():
            boto3.setup_default_session()
            session = boto3.DEFAULT_SESSION
            self.pill = placebo.attach(session, data_path=self.data_path)
            self.pill.stop()

            iam = boto3.client('iam')
            num_policies = 150

            for i in range(num_policies):
                iam.create_policy(PolicyName='test-{}'.format(i), PolicyDocument=self.test_policy)

            self.pill.record()
            paginator = iam.get_paginator('list_policies')
            list(paginator.paginate(Scope='Local'))

            p = Path(self.data_path)
            self.assertEqual(len(list(p.glob('*.json'))), 2)

            files = list(p.glob('*_1.json'))
            self.assertEqual(len(list(files)), 1)

            files = list(p.glob('*_100.json'))
            self.assertEqual(len(list(files)), 1)

            count = 0
            for file in p.iterdir():
                with open(file, 'r') as f:
                    result = json.load(f)
                    count += len(result['data']['Policies'])

            self.assertEqual(count, num_policies)