import sys

try:
    # `imp` was deprecated in 3.3, `find_spec` was introduced in 3.4, catch
    # future ImportErrors here.
    if sys.version_info.major == 3 and sys.version_info.minor > 3:
        raise DeprecationWarning
    import imp
except (ImportError, DeprecationWarning):
    import importlib.util

    # Cache names here, find_spec also iterates through `sys.meta_path` and will
    # recurse endlessly.
    _cache = []

    def _find_module(name, path):
        if name in _cache:
            raise ImportError
        _cache.append(name)
        spec = importlib.util.find_spec(name, path)
        if spec is not None:
            return spec.loader
else:
    # Continue using imp
    def _find_module(name, path):
        return imp.find_module(name, path)


class ErrorlessImport(object):
    '''Mocked importer, returns mocked modules

    This should be patched as the last finder in the :py:attr:`sys.meta_path`
    chain. When using :py:func:`imp.find_module`, the first import call will
    include the relative path -- i.e. for a module `foo.bar` importing
    `itertools`, the first lookup is for `foo.bar.itertools`. Because of this,
    we won't mock out anything in our namespace.

    If the module name is not in our namespace, and isn't successfully found
    using either :py:func:`imp.find_module` or :py:func:`importlib.find_spec`,
    on Python 2 and 3 respectively, we will mock the module out.
    '''

    def find_module(self, name, path=None):
        '''Find module, refer to self if we should mock the module'''
        try:
            module = _find_module(name, path)
            return module
        except ImportError:
            if name.startswith('readthedocs'):
                return None
            else:
                return self
        return None

    def load_module(self, fullname):
        if fullname not in sys.modules:
            sys.modules[fullname] = Mock()
        return sys.modules[fullname]


class Mock(object):
    def __repr__(self):
        return "<Silly Human, I'm not real>"

    def __eq__(self, b):
        return True

    def __getattr__(self, *args, **kwargs):
        return Mock()

    def __call__(self, *args, **kwargs):
        return Mock()


def patch_meta_path():
    sys.meta_path.append(ErrorlessImport())


def unpatch_meta_path():
    for loader in sys.meta_path:
        if isinstance(loader, ErrorlessImport):
            sys.meta_path.remove(loader)
