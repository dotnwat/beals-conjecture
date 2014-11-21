import cffi

_ffi = cffi.FFI()
_libbeal = _ffi.dlopen("./libbeal.so")
_ffi.cdef('''
uint32_t c_modpow(uint64_t base, uint64_t exponent, uint32_t mod);
unsigned int c_gcd(unsigned int u, unsigned int v);
void *cz_make(unsigned int maxb, unsigned int maxp, uint32_t mod);
void cz_free(void *czp);
uint32_t cz_get(void *czp, int c, int z);
bool cz_exists(void *czp, uint32_t val);
struct point { int a, x, b, y; };
void *axby_make(unsigned int maxb, unsigned int maxp, int a);
bool axby_next(void *axbyp, struct point *pp);
void axby_free(void *axbyp);
void *work_make(unsigned int maxb, unsigned int maxp, uint32_t *primes, size_t nprimes);
void work_free(void *workp);
size_t work_do_work(void *workp, int a, struct point *pts, size_t npts);
''')

def modpow(b, e, m):
    return _libbeal.c_modpow(b, e, m)

def gcd(u, v):
    return _libbeal.c_gcd(u, v)

class cz(object):
    def __init__(self, maxb, maxp, mod):
        self._p = _libbeal.cz_make(maxb, maxp, mod)

    def __del__(self):
        self.cleanup()

    def get(self, c, z):
        return _libbeal.cz_get(self._p, c, z)

    def exists(self, value):
        return _libbeal.cz_exists(self._p, value)

    def cleanup(self):
        if self._p:
            _libbeal.cz_free(self._p)
            self._p = None

class axby(object):
    def __init__(self, maxb, maxp, a):
        self._p = _libbeal.axby_make(maxb, maxp, a)
        self._point = _ffi.new('struct point [1]')

    def __del__(self):
        self.cleanup()

    def next(self):
        done = _libbeal.axby_next(self._p, self._point)
        if not done:
            return done, (self._point[0].a, self._point[0].x,
                    self._point[0].b, self._point[0].y)
        else:
            return done, None

    def cleanup(self):
        if self._p:
            _libbeal.axby_free(self._p)
            self._p = None

class search(object):
    def __init__(self, maxb, maxp, primes):
        self._p = _libbeal.work_make(maxb, maxp, primes, len(primes))
        self._points = _ffi.new('struct point [1000000]')
        self._max_base = maxb
        self._max_pow = maxp
        self._primes = primes

    def __del__(self):
        self.cleanup()

    def search(self, a):
        nresults = _libbeal.work_do_work(self._p, a, self._points, len(self._points))
        assert(nresults <= len(self._points))
        for i in range(0, nresults):
            yield (self._points[i].a, self._points[i].x, self._points[i].b,
                    self._points[i].y)

    def max_base(self):
        return self._max_base
    def max_pow(self):
        return self._max_pow
    def primes(self):
        return self._primes

    def cleanup(self):
        if self._p:
            _libbeal.work_free(self._p)
            self._p = None
