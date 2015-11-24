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


class FakeHttpResponse(object):

    def __init__(self, status_code):
        self.status_code = status_code


class MockClient(object):

    _mock_responses = {}

    def __init__(self, client):
        self.client = client
        self.client._endpoint.make_request = self.make_request

    def add_response(self, operation_name, response_data,
                     http_response=200):
        """
        Add a mocked response to an operation.  The ``operation_name``
        should be the name of the operation in the service API (e.g.
        DescribeInstances), the ``response_data`` should a value you want
        to return from a mocked call and the ``http_response`` should be
        the HTTP status code returned from the service.  You can add
        multiple responses for a given operation and they will be
        returned in order.
        """
        if operation_name not in self._mock_responses:
            self._mock_responses[operation_name] = {'index': 0,
                                                    'responses': []}
        self._mock_responses[operation_name]['responses'].append(
            (http_response, response_data))

    def make_request(self, model, request_dict):
        """
        A mocked out make_request call that bypasses all network calls
        and simply returns any mocked responses defined.
        """
        if model.name in self._mock_responses:
            responses = self._mock_responses[model.name]['responses']
            index = self._mock_responses[model.name]['index']
            index = min(index, len(responses) - 1)
            http_response, data = responses[index]
            self._mock_responses[model.name]['index'] += 1
        else:
            http_response, data = 200, {}
        return (FakeHttpResponse(http_response), data)


def mock_client(client):
    """
    Pass in a boto3 client and this function will turn it into a mocked
    client.  You can add mock responses using:

        client.mock.add_response(...)
    """
    client.mock = MockClient(client)
