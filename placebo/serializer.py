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

import json
import pickle
import datetime
from datetime import datetime, timedelta, tzinfo
from botocore.response import StreamingBody
from six import StringIO

class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)

utc = UTC()

class Format:
    """
    Serialization formats
    """
    JSON = "json"
    PICKLE = "pickle"

    DEFAULT = JSON
    ALLOWED = [JSON, PICKLE]


def deserialize(obj):
    """Convert JSON dicts back into objects."""
    # Be careful of shallow copy here
    target = dict(obj)
    class_name = None
    if '__class__' in target:
        class_name = target.pop('__class__')
    if '__module__' in obj:
        module_name = obj.pop('__module__')
    # Use getattr(module, class_name) for custom types if needed
    if class_name == 'datetime':
        return datetime(tzinfo=utc, **target)
    if class_name == 'StreamingBody':
        return StringIO(target['body'])
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
    if isinstance(obj, datetime):
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
        obj._raw_stream = StringIO(result['body'])
        obj._amount_read = 0
        return result
    # Raise a TypeError if the object isn't recognized
    raise TypeError("Type not serializable")


def json_serialize(obj, fp):
    """ Serialize ``obj`` as a JSON formatted stream to ``fp`` """
    json.dump(obj, fp, indent=4, default=serialize)


def json_deserialize(fp):
    """ Deserialize ``fp`` JSON content to a Python object."""
    return json.load(fp, object_hook=deserialize)


def get_serializer(serializer_format):
    """ Get the serializer for a specific format """
    if serializer_format == Format.JSON:
        return json_serialize
    if serializer_format == Format.PICKLE:
        return pickle.dump


def get_deserializer(serializer_format):
    """ Get the deserializer for a specific format """
    if serializer_format == Format.JSON:
        return json_deserialize
    if serializer_format == Format.PICKLE:
        return pickle.load
