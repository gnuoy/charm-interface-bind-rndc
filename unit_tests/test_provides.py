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


import unittest
import mock

import provides
import test_utils

_hook_args = {}


def mock_hook(*args, **kwargs):

    def inner(f):
        # remember what we were passed.  Note that we can't actually determine
        # the class we're attached to, as the decorator only gets the function.
        _hook_args[f.__name__] = dict(args=args, kwargs=kwargs)
        return f
    return inner


class MockConversation(object):

    def set_state(self, state):
        pass

    def remove_state(self, state):
        pass


class TestBindRNDCProvides(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._patched_hook = mock.patch('charms.reactive.hook', mock_hook)
        cls._patched_hook_started = cls._patched_hook.start()
        # force requires to rerun the mock_hook decorator:
        reload(provides)

    @classmethod
    def tearDownClass(cls):
        cls._patched_hook.stop()
        cls._patched_hook_started = None
        cls._patched_hook = None
        # and fix any breakage we did to the module
        reload(provides)

    def setUp(self):
        self.br = provides.BindRNDCProvides('some-relation', [])
        self._patches = {}
        self._patches_start = {}

    def tearDown(self):
        self.br = None
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch_br(self, attr, return_value=None):
        mocked = mock.patch.object(self.br, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)

    def test_registered_hooks(self):
        # test that the hooks actually registered the relation expressions that
        # are meaningful for this interface: this is to handle regressions.
        # The keys are the function names that the hook attaches to.
        hook_patterns = {
            'joined': ('{provides:bind-rndc}-relation-joined', ),
            'changed': ('{provides:bind-rndc}-relation-changed', ),
            'departed': ('{provides:bind-rndc}-relation-departed', ),
        }
        for k, v in _hook_args.items():
            self.assertEqual(hook_patterns[k], v['args'])

    def test_joined(self):
        self.patch_br('conversation')
        conv_mock = mock.MagicMock()
        self.conversation.return_value = conv_mock
        self.br.joined()
        conv_mock.set_state.assert_called_once_with(
            '{relation_name}.related'
        )

    def test_departed(self):
        self.patch_br('conversation')
        conv_mock = mock.MagicMock()
        self.conversation.return_value = conv_mock
        self.br.departed()
        conv_mock.remove_state.assert_called_once_with(
            '{relation_name}.related'
        )

    def test_send_rndckey_info(self):
        self.patch_br('conversations')
        conv_mock = mock.MagicMock()
        self.conversations.return_value = [conv_mock]
        with test_utils.patch_open() as (_open, _file):
            _file.readlines.return_value = ['algorithm hope', 'secret pass']
            self.br.send_rndckey_info()
        conv_mock.set_remote.assert_has_calls([
            mock.call('rndckey', 'pass'),
            mock.call('algorithm', 'hope'),
        ])

    def test_send_rndckey_info_no_info(self):
        self.patch_br('conversations')
        conv_mock = mock.MagicMock()
        self.conversations.return_value = [conv_mock]
        with test_utils.patch_open() as (_open, _file):
            _file.readlines.return_value = ['nothing useful']
            self.br.send_rndckey_info()
        conv_mock.set_remote.assert_has_calls([
            mock.call('rndckey', None),
            mock.call('algorithm', None),
        ])

    def test_client_ips(self):
        self.patch_br('conversation')
        self.patch_br('conversations')
        conv_mock = mock.MagicMock()
        conv_mock.get_remote.return_value = '10.0.0.10'
        self.conversations.return_value = [conv_mock]
        self.assertEqual(self.br.client_ips(), ['10.0.0.10'])
