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

import datetime
import unittest
import json

from io import StringIO, BytesIO

from botocore.response import StreamingBody

from placebo.serializer import serialize, deserialize, utc, Format
from placebo.serializer import get_serializer, get_deserializer
from placebo.serializer import _serialize_json, _deserialize_json
from placebo.serializer import _serialize_pickle, _deserialize_pickle


date_sample = {
    "LoginProfile": {
        "UserName": "baz",
        "CreateDate": datetime.datetime(2015, 1, 4, 9, 1, 2, 0, tzinfo=utc),
    }
}

date_json = """{"LoginProfile": {"CreateDate": {"__class__": "datetime", "day": 4, "hour": 9, "microsecond": 0, "minute": 1, "month": 1, "second": 2, "year": 2015}, "UserName": "baz"}}"""

content = b'this is a test'
stream = BytesIO(content)

streaming_body_sample = {
    'Body': StreamingBody(stream, len(content))
}

streaming_body_json = """{"Body": {"__class__": "StreamingBody", "__module__": "botocore.response", "body": "dGhpcyBpcyBhIHRlc3Q="}}"""


class TestSerializers(unittest.TestCase):

    def test_datetime_to_json(self):
        result = json.dumps(date_sample, default=serialize, sort_keys=True)
        self.assertEqual(result, date_json)

    def test_datetime_from_json(self):
        response = json.loads(date_json, object_hook=deserialize)
        self.assertEqual(response, date_sample)

    def test_streaming_body_to_json(self):
        result = json.dumps(
            streaming_body_sample, default=serialize, sort_keys=True)
        self.assertEqual(result, streaming_body_json)

    def test_streaming_body_from_json(self):
        response = json.loads(streaming_body_json, object_hook=deserialize)
        self.assertEqual(response['Body'].read(), content)

    def test_roundtrip_json(self):
        ser = get_serializer(Format.JSON)
        deser = get_deserializer(Format.JSON)
        fp = StringIO()
        ser(date_sample, fp)
        fp.seek(0)
        obj = deser(fp)
        self.assertEqual(obj, date_sample)

    def test_roundtrip_pickle(self):
        ser = get_serializer(Format.PICKLE)
        deser = get_deserializer(Format.PICKLE)
        fp = BytesIO()
        ser(date_sample, fp)
        fp.seek(0)
        obj = deser(fp)
        self.assertEqual(obj, date_sample)

    def test_get_serializer_json(self):
        ser = get_serializer(Format.JSON)
        self.assertEqual(ser, _serialize_json)

    def test_get_deserializer_json(self):
        ser = get_deserializer(Format.JSON)
        self.assertEqual(ser, _deserialize_json)

    def test_get_serializer_pickle(self):
        ser = get_serializer(Format.PICKLE)
        self.assertEqual(ser, _serialize_pickle)

    def test_get_deserialize_pickle(self):
        ser = get_deserializer(Format.PICKLE)
        self.assertEqual(ser, _deserialize_pickle)
