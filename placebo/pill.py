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
import os
import glob
import re

from placebo.serializer import serialize, deserialize


class FakeHttpResponse(object):

    def __init__(self, status_code):
        self.status_code = status_code


class Pill(object):

    def __init__(self, client, data_path):
        self.index_re = re.compile(r'.*_(?P<index>\d).json')
        self.client = client
        self.data_path = data_path
        if self.data_path:
            self.record()

    def start(self):
        # This is kind of sketchy.  We need to short-circuit the request
        # process in botocore so we don't make any network requests.  The
        # best way I have found is to mock out the make_request method of
        # the Endpoint associated with the client but this is not a public
        # attribute of the client so could change in the future.
        self._save_make_request = self.client._endpoint.make_request
        self.client._endpoint.make_request = self.make_request

    def stop(self):
        if self._save_mock_request:
            self.client.make_request = self._save_mock_request

    def _record_data(self, http_response, parsed, model, **kwargs):
        service_name = self.client.meta.service_model.endpoint_prefix
        operation_name = model.name
        self.add_response(service_name, operation_name, parsed,
                          http_response.status_code)

    def record(self):
        event = 'after-call.{}'.format(
            self.client.meta.service_model.endpoint_prefix)
        self.client.meta.events.register(event, self._record_data)

    def load(self, path):
        """
        Load a JSON document containing previously recorded mock responses.
        """
        # If passed a file-like object, use it directly.
        if hasattr(path, 'read'):
            self.mock_responses = json.load(path, object_hook=deserialize)
            return
        # If passed a string, treat it as a file path.
        with open(path, 'r') as fp:
            self.mock_responses = json.load(fp, object_hook=deserialize)

    def _get_file_path(self, data_dir, base_name):
        index = 0
        glob_pattern = os.path.join(data_dir, base_name + '*')
        for file_path in glob.glob(glob_pattern):
            file_name = os.path.basename(file_path)
            m = self.index_re.match(file_name)
            if m:
                i = int(m.group('index'))
                if i > index:
                    index = i
        index += 1
        return os.path.join(data_dir, '{}_{}.json'.format(base_name, index))

    def add_response(self, service_name, operation_name, response_data,
                     http_response=200):
        """
        Store a response to the data directory.  The ``operation_name``
        should be the name of the operation in the service API (e.g.
        DescribeInstances), the ``response_data`` should a value you want
        to return from a placebo call and the ``http_response`` should be
        the HTTP status code returned from the service.  You can add
        multiple responses for a given operation and they will be
        returned in order.
        """
        base_name = '{}.{}'.format(service_name, operation_name)
        filepath = self._get_file_path(self.data_path, base_name)
        json_data = {'status_code': http_response,
                     'data': response_data}
        with open(filepath, 'w') as fp:
            json.dump(json_data, fp, indent=4, default=serialize)

    def make_request(self, model, request_dict):
        """
        A mocked out make_request call that bypasses all network calls
        and simply returns any mocked responses defined.
        """
        key = '{}.{}'.format(self.client.meta.service_model.endpoint_prefix,
                             model.name)
        if key in self.mock_responses:
            responses = self.mock_responses[key]['responses']
            index = self.mock_responses[key]['index']
            index = min(index, len(responses) - 1)
            http_response, data = responses[index]
            self.mock_responses[key]['index'] += 1
        else:
            http_response, data = 200, {}
        return (FakeHttpResponse(http_response), data)
