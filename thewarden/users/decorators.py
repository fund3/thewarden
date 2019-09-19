import collections
import functools
import hashlib
import inspect
import os
import time
from functools import wraps
from glob import glob

from thewarden.config import Config

import pandas as pd


def clean_all():
    # pandas memoization clean
    del_cached()


def pd_cache(func):
    # Caches a Pandas DF into file for later use
    # Memoization version for pandas DF
    try:
        os.mkdir('.pd_cache')
    except FileExistsError:
        pass

    @wraps(func)
    def cache(*args, **kw):
        # Get raw code of function as str and hash it
        func_code = ''.join(inspect.getsourcelines(func)[0]).encode('utf-8')
        hsh = hashlib.md5(func_code).hexdigest()[:6]
        f = '.pd_cache/' + func.__name__ + '_' + hsh + '.pkl'
        if os.path.exists(f):
            df = pd.read_pickle(f)
            return df

        # Delete any file name that has `cached_[func_name]_[6_chars]_.pkl`
        for cached in glob(f'./.pd_cache/{func.__name__}_*.pkl'):
            if (len(cached) - len(func.__name__)) == 20:
                os.remove(cached)
        # Write new
        df = func(*args, **kw)
        df.to_pickle(f)
        return df

    return cache


def del_cached():
    cached = os.listdir('./.pd_cache/')
    if len(cached) > 0:
        [os.remove(x) for x in cached]


def timing(method):
    # Time a function - only runs if environment variable:
    # WARDEN_STATUS="developer
    def timed(*args, **kw):
        if Config.WARDEN_STATUS == "developer":
            ts = time.time()
            result = method(*args, **kw)
            te = time.time()
            print('\033[92mFunction', method.__name__, '\033[95mtime:',
                  round((te - ts) * 1000, 1), 'ms')
            return result
        else:
            return (method(*args, **kw))

    return timed


class memoized(object):
    # Decorator. Caches a function's return value each time it is called.
    # If called later with the same arguments, the cached value is returned
    # (not reevaluated).
    def __init__(self, func):
        # Initiliaze Memoization for this function
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        if not isinstance(args, collections.Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func(*args)
        if args in self.cache:
            return self.cache[args]
        else:
            value = self.func(*args)
            self.cache[args] = value
            return value

    def __repr__(self):
        return self.func.__doc__

    def __get__(self, obj, objtype):
        return functools.partial(self.__call__, obj)

    # Clears the cache - called when there are changes that may affect the result
    # of the function
    def clear(self):
        if Config.WARDEN_STATUS == "developer":
            print(f"cleared Cache for {self.func}")
        self.cache = {}


class MWT(object):
    # Decorator that caches the result of a function until a given timeout (in seconds)
    # Helpful when running complicated calculations that are used more than once
    # Source: http://code.activestate.com/recipes/325905-memoize-decorator-with-timeout/
    _caches = {}
    _timeouts = {}

    def __init__(self, timeout=2):
        self.timeout = timeout

    def collect(self):
        # Clear cache of results which have timed out
        for func in self._caches:
            cache = {}
            for key in self._caches[func]:
                if (time.time() -
                        self._caches[func][key][1]) < self._timeouts[func]:
                    cache[key] = self._caches[func][key]
            self._caches[func] = cache

    def __call__(self, f):
        self.cache = self._caches[f] = {}
        self._timeouts[f] = self.timeout

        def func(*args, **kwargs):
            kw = sorted(kwargs.items())
            key = (args, tuple(kw))
            if Config.WARDEN_STATUS == "developer":
                print("\033[92mMemoization (MWT, timeout=" +
                      str(self.timeout) + "): \033[95m" + (f.__name__) +
                      "\033[94m(" + str(key) + ")")
            try:
                # Using memoized function only if still on time
                v = self.cache[key]
                if (time.time() - v[1]) > self.timeout:
                    if Config.WARDEN_STATUS == "developer":
                        print("             \033[93mTimed out")
                    raise KeyError
                else:
                    if Config.WARDEN_STATUS == "developer":
                        print("             \033[92mUsing Cached result")
            except (KeyError, TypeError):
                # Need to recalculate
                try:
                    v = self.cache[key] = f(*args, **kwargs), time.time()
                    if Config.WARDEN_STATUS == "developer":
                        print("             \033[92mRecalc and Stored OK")
                except TypeError:  # Some args passed as list return TypeError, skip
                    if Config.WARDEN_STATUS == "developer":
                        print(
                            "             \033[91mType Error - could not store"
                        )
                    return (f(*args, **kwargs))
            return v[0]

        func.func_name = f.__name__

        return func
