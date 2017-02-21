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

import datetime
import unittest
import json

from placebo.serializer import serialize, deserialize, utc


date_sample = {
    "LoginProfile": {
        "UserName": "baz",
        "CreateDate": datetime.datetime(2015, 1, 4, 9, 1, 2, 0, tzinfo=utc),
    }
}

date_json = """{"LoginProfile": {"CreateDate": {"__class__": "datetime", "day": 4, "hour": 9, "microsecond": 0, "minute": 1, "month": 1, "second": 2, "year": 2015}, "UserName": "baz"}}"""


class TestSerializers(unittest.TestCase):

    def test_datetime_to_json(self):
        result = json.dumps(date_sample, default=serialize, sort_keys=True)
        self.assertEqual(result, date_json)

    def test_datetime_from_json(self):
        response = json.loads(date_json, object_hook=deserialize)
        self.assertEqual(response, date_sample)
