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
import hashlib
import json
import os
import re
import copy
import uuid
import logging
from typing import List, Dict

from placebo.serializer import Format, get_deserializer, get_serializer

LOG = logging.getLogger(__name__)
DebugFmtString = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class FakeHttpResponse(object):

    def __init__(self, status_code):
        self.status_code = status_code


def _filter_hash(unfiltered: Dict, keys: List[str]) -> Dict:
    filtered = {}
    for key in keys:
        filtered[key] = unfiltered[key]
    return filtered


class Pill(object):
    clients = []

    def __init__(self, prefix=None, debug=False, record_format=Format.JSON):
        if debug:
            self._set_logger(__name__, logging.DEBUG)

        record_format = record_format.lower()
        if record_format not in Format.ALLOWED:
            LOG.warning("Record format not allowed. Falling back to default.")
            record_format = Format.DEFAULT

        self._serializer = get_serializer(record_format)
        self._filename_re = re.compile(r'.*\..*.{0}'.format(
            record_format))
        self._record_format = record_format
        self.prefix = prefix
        self._uuid = str(uuid.uuid4())
        self._data_path = None
        self._mode = None
        self._services = ""
        self._operations = ""
        self._session = None
        self.events = {}
        self.clients = []

    @property
    def mode(self):
        return self._mode

    @property
    def data_path(self):
        return self._data_path

    @property
    def session(self):
        return self._session

    @property
    def record_format(self):
        return self._record_format

    @staticmethod
    def _set_logger(logger_name, level=logging.INFO):
        """
        Convenience function to quickly configure full debug output
        to go to the console.
        """
        log = logging.getLogger(logger_name)
        log.setLevel(level)

        ch = logging.StreamHandler(None)
        ch.setLevel(level)

        formatter = logging.Formatter(DebugFmtString)

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        log.addHandler(ch)

    def _create_shim_class(self):
        # This is kind of tricky.  Maybe too tricky.
        # We want to know about all of the clients that are created within
        # the session we are attached to.  To do that, we dynamically
        # create a Class object that will become a superclass of each
        # new client that gets created.  This superclass has an __init__
        # method that appends the new client instance into this Pill
        # instance's list of clients.  The ugly code messing around with
        # mro() is there because we have to define an __init__ method in
        # our dynamically created class so we have to make sure it
        # calls it's superclass's __init__ methods.  We can't use
        # super() because that needs the class (which we are in the process
        # of creating) so we walk the method resolution order to find
        # our superclass.  The funny business with foo is because the
        # self inside _init_method stomps on the self defined in the
        # scope of this method but we really just need a reference to
        # the the method for adding a client.
        foo = self.add_client

        def _init_method(self, *args, **kwargs):
            res_order = self.__class__.mro()
            for i, cls in enumerate(res_order):
                if cls.__name__ == 'PillShim':
                    break
            super_cls_index = i + 1
            if len(res_order) >= super_cls_index + 1:
                super_cls = res_order[super_cls_index]
                super_cls.__init__(self, *args, **kwargs)
            foo(self)

        class_attributes = {'__init__': _init_method}
        bases = []
        class_name = 'PillShim'
        cls = type(class_name, tuple(bases), class_attributes)
        return cls

    def _create_client(self, class_attributes, base_classes, **kwargs):
        LOG.debug('_create_client')
        base_classes.insert(0, self._create_shim_class())

    def add_client(self, client):
        self.clients.append(client)

    def attach(self, session, data_path):
        LOG.debug('attaching to session: %s', session)
        LOG.debug('datapath: %s', data_path)
        self._session = session
        self._data_path = data_path
        session.events.register('creating-client-class', self._create_client)

    def _registered(self, service_name: str, operation_name: str) -> bool:
        """
        Returns true if the service_name and operation_name match the regex
        pattern used with record(). This is meant to be called from the handlers
        as a workaround for boto3 not supporting globbing natively.
        """
        if re.match(self._services, service_name) and re.match(self._operations, operation_name):
            LOG.debug('Handling Event: %s -- %s', service_name, operation_name)
            return True
        else:
            LOG.debug('Ignoring Event: %s -- %s', service_name, operation_name)
            return False

    def record(self, services='.*', operations='.*'):
        """
        Record start's recording event's to the filesystem. You can use regex
        expressions for services and operations, however the filtering is done
        in the handler's itself.
        """
        if self._mode == 'playback':
            self.stop()
        self._mode = 'record'

        # You can't register event's with normal globbing, but we can store our original
        # pattern and check it in the handler to get the same behavior.
        self._services = services
        self._operations = operations

        self._register('record', 'before-call', "*", "*", self._record_params)
        self._register('record', 'after-call', "*", "*", self._record_data)

    def _register(self, mode, event_name, operation, service, function):
        name = '{0}.{1}.{2}'.format(event_name, service.strip(), operation.strip())
        unique_id = 'placebo-{}-mode-{}-{}'.format(mode, event_name, function.__name__)
        LOG.debug('recording: %s -- %s', name, unique_id)
        self.events[name] = unique_id
        self._session.events.register(name, function, unique_id)
        for client in self.clients:
            client.meta.events.register(name, function, unique_id)

    def playback(self):
        if self.mode == 'record':
            self.stop()
        if self.mode is None:
            self._mode = 'playback'
            self._register('playback', 'before-call', '*', '*', self._record_params)
            self._register('playback', 'before-call', '*', '*', self._mock_request)

    def stop(self):
        LOG.debug('stopping, mode=%s', self.mode)
        if self._session:
            for name, unique_id in self.events.items():
                self._session.events.unregister(name, unique_id=unique_id)
                for client in self.clients:
                    client.meta.events.unregister(name, unique_id=unique_id)
            self.events = {}
        self._mode = None

    def _record_params(self, params, context, model, **kwargs):
        service_name = model.service_model.endpoint_prefix
        operation_name = model.name
        if not self._registered(service_name, operation_name):
            return

        p = copy.deepcopy(params)  # Be careful not to modify the original
        p = _filter_hash(p, ["url_path", "query_string", "method", "body", "url"])
        p["client_region"] = context["client_region"]
        params_h = json.dumps(p).encode()
        context["_pill_params_hash"] = hashlib.sha256(params_h).hexdigest()
        LOG.debug('_record_params')

    def _record_data(self, http_response, parsed, model, context, **kwargs):
        LOG.debug('_record_data')
        service_name = model.service_model.endpoint_prefix
        operation_name = model.name
        if not self._registered(service_name, operation_name):
            return
        params_hash = context["_pill_params_hash"]
        self.save_response(service_name, operation_name, params_hash,
                           parsed, http_response.status_code)

    def get_new_file_path(self, service, operation, params_hash):
        base_name = '{0}.{1}.{2}'.format(service, operation, params_hash)
        if self.prefix:
            base_name = '{0}.{1}'.format(self.prefix, base_name)

        return os.path.join(
            self._data_path,
            '{0}.{1}'.format(base_name, self.record_format)
        )

    @staticmethod
    def find_file_format(file_name):
        """
        Returns a tuple with the file path and format found, or (None, None)
        """
        for file_format in Format.ALLOWED:
            file_path = '.'.join((file_name, file_format))
            if os.path.exists(file_path):
                return file_path, file_format
        return None, None

    def get_next_file_path(self, service, operation, params_hash):
        """
        Returns a tuple with the next file to read and the serializer
        format used
        """
        base_name = '{0}.{1}.{2}'.format(service, operation, params_hash)
        if self.prefix:
            base_name = '{0}.{1}'.format(self.prefix, base_name)
        file_path = os.path.join(self.data_path, base_name)
        LOG.debug('get_next_file_path: %s', file_path)

        next_file, serializer_format = self.find_file_format(file_path)
        if not next_file:
            raise IOError('response file ({0}.[{1}]) not found'.format(
                file_path, "|".join(Format.ALLOWED)))

        return next_file, serializer_format

    def save_response(self, service, operation, params_hash,
                      response_data, http_response=200):
        """
        Store a response to the data directory.  The ``operation``
        should be the name of the operation in the service API (e.g.
        DescribeInstances), the ``response_data`` should a value you want
        to return from a placebo call and the ``http_response`` should be
        the HTTP status code returned from the service.  You can add
        multiple responses for a given operation and they will be
        returned in order.
        """
        LOG.debug('save_response: %s.%s.%s', service, operation, params_hash)

        # TODO: tests
        filepath = self.get_new_file_path(service, operation, params_hash)

        LOG.debug('save_response: path=%s', filepath)
        data = {'status_code': http_response,
                'data': response_data}

        dir = os.path.dirname(filepath)
        if not os.path.exists(dir):
            os.mkdir(dir)

        with open(filepath, Format.write_mode(self.record_format)) as fp:
            self._serializer(data, fp)

    def load_response(self, service, operation, params_hash):
        LOG.debug('load_response: %s.%s.%s', service, operation, params_hash)
        (response_file, file_format) = self.get_next_file_path(
            service, operation, params_hash)
        LOG.debug('load_responses: %s', response_file)
        with open(response_file, Format.read_mode(file_format)) as fp:
            response_data = get_deserializer(file_format)(fp)
        return (FakeHttpResponse(response_data['status_code']),
                response_data['data'])

    def _mock_request(self, context, params, **kwargs):
        """
        A mocked out make_request call that bypasses all network calls
        and simply returns any mocked responses defined.
        """
        model = kwargs.get('model')
        service = model.service_model.endpoint_prefix
        operation = model.name
        params_hash = context["_pill_params_hash"]
        LOG.debug('_make_request: %s.%s.%s', service, operation, params_hash)
        return self.load_response(service, operation, params_hash)
