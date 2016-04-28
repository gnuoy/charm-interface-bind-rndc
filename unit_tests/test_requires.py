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

import requires


_hook_args = {}


def mock_hook(*args, **kwargs):

    def inner(f):
        # remember what we were passed.  Note that we can't actually determine
        # the class we're attached to, as the decorator only gets the function.
        _hook_args[f.__name__] = dict(args=args, kwargs=kwargs)
        return f
    return inner


class TestBindRNDCRequires(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._patched_hook = mock.patch('charms.reactive.hook', mock_hook)
        cls._patched_hook_started = cls._patched_hook.start()
        # force requires to rerun the mock_hook decorator:
        reload(requires)

    @classmethod
    def tearDownClass(cls):
        cls._patched_hook.stop()
        cls._patched_hook_started = None
        cls._patched_hook = None
        # and fix any breakage we did to the module
        reload(requires)

    def setUp(self):
        self.br = requires.BindRNDCRequires('some-relation', [])
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
            'joined': ('{requires:bind-rndc}-relation-joined', ),
            'changed': ('{requires:bind-rndc}-relation-changed', ),
            'departed_or_broken':
                ('{requires:bind-rndc}-relation-{broken,departed}', ),
        }
        for k, v in _hook_args.items():
            self.assertEqual(hook_patterns[k], v['args'])

    def test_changed_complete(self):
        self.patch_br('set_state')
        self.patch_br('data_complete', True)
        self.br.changed()
        self.set_state.assert_has_calls([
            mock.call('{relation_name}.connected'),
            mock.call('{relation_name}.available'),
        ])

    def test_changed_incomplete(self):
        self.patch_br('set_state')
        self.patch_br('data_complete', False)
        self.br.changed()
        self.set_state.assert_called_once_with('{relation_name}.connected')

    def test_departed_incomplete(self):
        self.patch_br('remove_state')
        self.patch_br('data_complete', True)
        self.br.departed_or_broken()
        self.remove_state.assert_called_once_with('{relation_name}.connected')

    def test_departed_complete(self):
        self.patch_br('remove_state')
        self.patch_br('data_complete', False)
        self.br.departed_or_broken()
        self.remove_state.assert_has_calls([
            mock.call('{relation_name}.connected'),
            mock.call('{relation_name}.available'),
        ])

    def test_data_complete(self):
        self.patch_br('algorithm', 'hmac-md5')
        self.patch_br('rndckey', 'supersecret')
        self.patch_br('private_address', '10.0.0.10')
        assert self.br.data_complete() is True
        self.rndckey.return_value = None
        assert self.br.data_complete() is False
