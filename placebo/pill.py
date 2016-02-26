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
import uuid
import logging

from placebo.serializer import serialize, deserialize

LOG = logging.getLogger(__name__)
DebugFmtString = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class FakeHttpResponse(object):

    def __init__(self, status_code):
        self.status_code = status_code


class Pill(object):

    clients = []

    def __init__(self, prefix=None, debug=False):
        if debug:
            self._set_logger(__name__, logging.DEBUG)
        self.filename_re = re.compile(r'.*\..*_(?P<index>\d+).json')
        self.prefix = prefix
        self._uuid = str(uuid.uuid4())
        self._data_path = None
        self._mode = None
        self._session = None
        self._index = {}
        self.events = []
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

    def _set_logger(self, logger_name, level=logging.INFO):
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

    def record(self, services='*', operations='*'):
        if self._mode == 'playback':
            self.stop()
        self._mode = 'record'
        for service in services.split(','):
            for operation in operations.split(','):
                event = 'after-call.{0}.{1}'.format(
                    service.strip(), operation.strip())
                LOG.debug('recording: %s', event)
                self.events.append(event)
                self._session.events.register(
                    event, self._record_data, 'placebo-record-mode')
                for client in self.clients:
                    client.meta.events.register(
                        event, self._record_data, 'placebo-record-mode')

    def playback(self):
        if self.mode == 'record':
            self.stop()
        if self.mode is None:
            event = 'before-call.*.*'
            self.events.append(event)
            self._session.events.register(
                event, self._mock_request, 'placebo-playback-mode')
            self._mode = 'playback'
            for client in self.clients:
                client.meta.events.register(
                    event, self._mock_request, 'placebo-playback-mode')

    def stop(self):
        LOG.debug('stopping, mode=%s', self.mode)
        if self.mode == 'record':
            if self._session:
                for event in self.events:
                    self._session.events.unregister(
                        event, unique_id='placebo-record-mode')
                    for client in self.clients:
                        client.meta.events.unregister(
                            event, unique_id='placebo-record-mode')
                self.events = []
        elif self.mode == 'playback':
            if self._session:
                for event in self.events:
                    self._session.events.unregister(
                        event, unique_id='placebo-playback-mode')
                    for client in self.clients:
                        client.meta.events.unregister(
                            event, unique_id='placebo-playback-mode')
                self.events = []
        self._mode = None

    def _record_data(self, http_response, parsed, model, **kwargs):
        LOG.debug('_record_data')
        service_name = model.service_model.endpoint_prefix
        operation_name = model.name
        self.save_response(service_name, operation_name, parsed,
                           http_response.status_code)

    def get_new_file_path(self, service, operation):
        base_name = '{0}.{1}'.format(service, operation)
        if self.prefix:
            base_name = '{0}.{1}'.format(self.prefix, base_name)
        LOG.debug('get_new_file_path: %s', base_name)
        index = 0
        glob_pattern = os.path.join(self._data_path, base_name + '*')
        for file_path in glob.glob(glob_pattern):
            file_name = os.path.basename(file_path)
            m = self.filename_re.match(file_name)
            if m:
                i = int(m.group('index'))
                if i > index:
                    index = i
        index += 1
        return os.path.join(
            self._data_path, '{0}_{1}.json'.format(base_name, index))

    def get_next_file_path(self, service, operation):
        base_name = '{0}.{1}'.format(service, operation)
        if self.prefix:
            base_name = '{0}.{1}'.format(self.prefix, base_name)
        LOG.debug('get_next_file_path: %s', base_name)
        next_file = None
        while next_file is None:
            index = self._index.setdefault(base_name, 1)
            fn = os.path.join(
                self._data_path, base_name + '_{0}.json'.format(index))
            if os.path.exists(fn):
                next_file = fn
                self._index[base_name] += 1
            elif index != 1:
                self._index[base_name] = 1
            else:
                # we are looking for the first index and it's not here
                raise IOError('response file ({0}) not found'.format(fn))
        return fn

    def save_response(self, service, operation, response_data,
                      http_response=200):
        """
        Store a response to the data directory.  The ``operation``
        should be the name of the operation in the service API (e.g.
        DescribeInstances), the ``response_data`` should a value you want
        to return from a placebo call and the ``http_response`` should be
        the HTTP status code returned from the service.  You can add
        multiple responses for a given operation and they will be
        returned in order.
        """
        LOG.debug('save_response: %s.%s', service, operation)
        filepath = self.get_new_file_path(service, operation)
        LOG.debug('save_response: path=%s', filepath)
        json_data = {'status_code': http_response,
                     'data': response_data}
        with open(filepath, 'w') as fp:
            json.dump(json_data, fp, indent=4, default=serialize)

    def load_response(self, service, operation):
        LOG.debug('load_response: %s.%s', service, operation)
        response_file = self.get_next_file_path(service, operation)
        LOG.debug('load_responses: %s', response_file)
        with open(response_file, 'r') as fp:
            response_data = json.load(fp, object_hook=deserialize)
        return (FakeHttpResponse(response_data['status_code']),
                response_data['data'])

    def _mock_request(self, **kwargs):
        """
        A mocked out make_request call that bypasses all network calls
        and simply returns any mocked responses defined.
        """
        model = kwargs.get('model')
        service = model.service_model.endpoint_prefix
        operation = model.name
        LOG.debug('_make_request: %s.%s', service, operation)
        return self.load_response(service, operation)
