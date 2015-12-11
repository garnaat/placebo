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

from placebo.pill import Pill


_data_path = None
_mode = None


class PlaceboClient(object):

    def __init__(self, *args, **kwargs):
        global data_path
        super(PlaceboClient, self).__init__(*args, **kwargs)
        self.meta.pill = Pill(self, data_path)


def _add_custom_class(base_classes, **kwargs):
    base_classes.insert(0, PlaceboClient)


def record(data_path):
    global _data_path, _mode
    _data_path = data_path
    _mode = 'record'


def playback(data_path):
    global _data_path, _mode
    _data_path = data_path
    _mode = 'playback'


def attach(session):
    session.events.register('creating-client-class', _add_custom_class)
