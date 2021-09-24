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
import pickle
import datetime
import base64
from io import BytesIO

from botocore.response import StreamingBody


class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)

utc = UTC()


class Format:
    """
    Serialization formats
    """
    JSON = "json"
    PICKLE = "pickle"

    DEFAULT = JSON
    ALLOWED = [JSON, PICKLE]

    @classmethod
    def read_mode(cls, format):
        """
        Return the correct read mode for this type of format.
        """
        if format == cls.PICKLE:
            return 'rb'
        else:
            return 'r'

    @classmethod
    def write_mode(cls, format):
        """
        Return the correct write mode for this type of format.
        """
        if format == cls.PICKLE:
            return 'wb'
        else:
            return 'w'


def deserialize(obj):
    """Convert JSON dicts back into objects."""
    # Be careful of shallow copy here
    target = dict(obj)
    class_name = None
    if '__class__' in target:
        class_name = target.pop('__class__')
    if '__module__' in obj:
        obj.pop('__module__')
    # Use getattr(module, class_name) for custom types if needed
    if class_name == 'datetime':
        return datetime.datetime(tzinfo=utc, **target)
    if class_name == 'StreamingBody':
        b64_body = obj['body']
        decoded_body = base64.b64decode(b64_body)
        return BytesIO(decoded_body)
    # Return unrecognized structures as-is
    return obj


def serialize(obj):
    """Convert objects into JSON structures."""
    # Record class and module information for deserialization
    result = {'__class__': obj.__class__.__name__}
    try:
        result['__module__'] = obj.__module__
    except AttributeError:
        pass
    # Convert objects to dictionary representation based on type
    print('+++++ %s' % obj)
    print('+++++ %s' % type(obj))
    if isinstance(obj, datetime.datetime):
        result['year'] = obj.year
        result['month'] = obj.month
        result['day'] = obj.day
        result['hour'] = obj.hour
        result['minute'] = obj.minute
        result['second'] = obj.second
        result['microsecond'] = obj.microsecond
        return result
    if isinstance(obj, StreamingBody):
        result['body'] = obj.read()
        obj._raw_stream = BytesIO(result['body'])
        obj._amount_read = 0
        return result
    if isinstance(obj, bytes):
        encoded = base64.b64encode(obj)
        return encoded.decode('utf-8')
    # Raise a TypeError if the object isn't recognized
    raise TypeError("Type not serializable")


def _serialize_json(obj, fp):
    """ Serialize ``obj`` as a JSON formatted stream to ``fp`` """
    json.dump(obj, fp, indent=4, default=serialize)


def _deserialize_json(fp):
    """ Deserialize ``fp`` JSON content to a Python object."""
    return json.load(fp, object_hook=deserialize)


def _serialize_pickle(obj, fp):
    """ Serialize ``obj`` as a PICKLE formatted stream to ``fp`` """
    pickle.dump(obj, fp)


def _deserialize_pickle(fp):
    """ Deserialize ``fp`` PICKLE content to a Python object."""
    return pickle.load(fp)


def get_serializer(serializer_format):
    """ Get the serializer for a specific format """
    if serializer_format == Format.JSON:
        return _serialize_json
    if serializer_format == Format.PICKLE:
        return _serialize_pickle


def get_deserializer(serializer_format):
    """ Get the deserializer for a specific format """
    if serializer_format == Format.JSON:
        return _deserialize_json
    if serializer_format == Format.PICKLE:
        return _deserialize_pickle
