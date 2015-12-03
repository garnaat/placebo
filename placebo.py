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


def _add_custom_class(base_classes, **kwargs):
    base_classes.insert(0, PlaceboClient)


class FakeHttpResponse(object):

    def __init__(self, status_code):
        self.status_code = status_code


class Placebo(object):

    _mock_responses = {}

    def __init__(self, client):
        self.client = client

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

    def _record_data(self, http_response, parsed, **kwargs):
        _, service_name, operation_name = kwargs['event_name'].split('.')
        self.add_response(service_name, operation_name, parsed,
                          http_response.status_code)

    def record(self):
        event = 'after-call.{}'.format(
            self.client.meta.service_model.endpoint_prefix)
        self.client.meta.events.register(event, self._record_data)

    def save(self, path):
        with open(path, 'w') as fp:
            json.dump(self._mock_responses, fp, indent=4)

    def load(self, path):
        with open(path, 'r') as fp:
            self._mock_responses = json.load(fp)

    def add_response(self, service_name, operation_name, response_data,
                     http_response=200):
        """
        Add a placebo response to an operation.  The ``operation_name``
        should be the name of the operation in the service API (e.g.
        DescribeInstances), the ``response_data`` should a value you want
        to return from a placebo call and the ``http_response`` should be
        the HTTP status code returned from the service.  You can add
        multiple responses for a given operation and they will be
        returned in order.
        """
        key = '{}.{}'.format(service_name, operation_name)
        if key not in self._mock_responses:
            self._mock_responses[key] = {'index': 0,
                                         'responses': []}
        self._mock_responses[key]['responses'].append(
            (http_response, response_data))

    def make_request(self, model, request_dict):
        """
        A mocked out make_request call that bypasses all network calls
        and simply returns any mocked responses defined.
        """
        key = '{}.{}'.format(self.client.meta.service_model.endpoint_prefix,
                             model.name)
        if key in self._mock_responses:
            responses = self._mock_responses[key]['responses']
            index = self._mock_responses[key]['index']
            index = min(index, len(responses) - 1)
            http_response, data = responses[index]
            self._mock_responses[key]['index'] += 1
        else:
            http_response, data = 200, {}
        return (FakeHttpResponse(http_response), data)


class PlaceboClient(object):

    def __init__(self, *args, **kwargs):
        super(PlaceboClient, self).__init__(*args, **kwargs)
        self.meta.placebo = Placebo(self)


def attach(session):
    session.events.register('creating-client-class', _add_custom_class)
