import random
import fractions
import unittest
import cffi
import os

ffi = cffi.FFI()
libbeal = ffi.dlopen("./libbeal.so")
ffi.cdef('''
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
''')

# run fast tests?
_FAST = False
if os.environ.get("FAST") == "1":
    _FAST = True

class TestModPow(unittest.TestCase):
    def __check(self, b, e, m):
        value1 = pow(b, e, m)
        value2 = libbeal.c_modpow(b, e, m)
        self.assertEqual(value1, value2,
                "%d != %d: %d %d %d" % (value1, value2, b, e, m))

    def test_dense(self):
        # 2,3,4,5x100 -> 3s,12s,30s,1m
        limit = 200 if _FAST else 500
        for base in range(1, limit):
            for expo in range(1, limit):
                for mod in range(1, limit):
                    self.__check(base, expo, mod)

    def test_random(self):
        # 10K,1M,10M -> .5s,11s,2m
        limit = 10**4 if _FAST else 10**7
        for _ in range(limit):
            base = random.randint(1, 2**64-1)
            expo = random.randint(1, 2**64-1)
            mod = random.randint(1, 2**32-1)
            self.__check(base, expo, mod)

    def test_specific(self):
        # random testing found a problem with c_modpow for these inputs. the
        # fix was to include `base = base % mod` before starting the loop in
        # the modpow algo, as is done in the wikipedia algorithm.
        self.__check(4542062976100348463, 4637193517411546665, 3773338459)
        self.__check(70487458014159955, 5566498974156504764, 3541295600)

class TestGCD(unittest.TestCase):
    def __check(self, u, v):
        value1 = fractions.gcd(u, v)
        value2 = libbeal.c_gcd(u, v)
        self.assertEqual(value1, value2, "%u %u" % (u, v))

    def test_dense(self):
        # 1K,10K -> .5s,40s
        limit = 10**3 if _FAST else 10**4
        for u in xrange(1, limit):
            for v in xrange(1, limit):
                self.__check(u, v)

    def test_random(self):
        # 1M,10M,100M -> 1.2s,10s,1m40s
        limit = 10**6 if _FAST else 10**8
        for _ in xrange(limit):
            u = random.randint(1, 2**32-1)
            v = random.randint(1, 2**32-1)
            self.__check(u, v)

class TestCz(unittest.TestCase):
    def __check(self, maxb, maxp, mod, fast=False):
        czp = libbeal.cz_make(maxb, maxp, mod)

        values = set()
        for c in xrange(1, maxb+1):
            for z in xrange(3, maxp+1):
                value1 = pow(c, z, mod)
                value2 = libbeal.cz_get(czp, c, z)
                self.assertEqual(value1, value2)
                values.add(value2)
        assert len(values) > 0

        # assert that every value in c^z is set in the exists set
        for value in values:
            exists = libbeal.cz_exists(czp, value)
            self.assertTrue(exists)

        # iterating over all 2^32 positions in the exists set is expensive so
        # we just perform a random sampling. anything that isn't false should
        # be in the exists set we calculated above from the cz table
        # 10M,100M -> 1.3s,12s,
        limit = 10**6 if fast else 10**8
        for _ in xrange(limit):
            value = random.randint(0, 2**32-1)
            exists = libbeal.cz_exists(czp, value)
            if exists:
                self.assertTrue(value in values)

        libbeal.cz_free(czp)

    def test_random(self):
        limit = 2 if _FAST else 40
        for _ in xrange(limit):
            maxb = random.randint(1, 2000)
            maxp = random.randint(3, 2000)
            mod = random.randint(1, 2**32-1)
            self.__check(maxb, maxp, mod, True)

    def test_specific(self):
        self.__check(1000, 1000, 4294967291)
        self.__check(1000, 1000, 4294967279)
        self.__check(2000, 2000, 4294967279)
        self.__check(2000, 2000, 2**32-1)

    def test_dense(self):
        for maxb in range(1, 12):
            for maxp in range(3, 12):
                self.__check(maxb, maxp, 4294967291, True)
        for maxb in range(1, 12):
            self.__check(maxb, 100000, 4294967291, True)
        for maxp in range(3, 14):
            self.__check(100000, maxp, 4294967291, True)

class TestAxby(unittest.TestCase):
    def test_all_points(self):
        maxb = 200
        maxp = 200
        point = ffi.new('struct point [1]')
        for a in xrange(1, maxb+1):
            p = libbeal.axby_make(maxb, maxp, a)
            for b in xrange(1, a+1):
                if fractions.gcd(a, b) > 1:
                    continue
                for x in xrange(3, maxp+1):
                    for y in xrange(3, maxp+1):
                        done = libbeal.axby_next(p, point)
                        assert(not done)
                        self.assertEqual(a, point[0].a)
                        self.assertEqual(x, point[0].x)
                        self.assertEqual(b, point[0].b)
                        self.assertEqual(y, point[0].y)
            done = libbeal.axby_next(p, point)
            assert(done)
            libbeal.axby_free(p)


if __name__ == '__main__':
    unittest.main()
