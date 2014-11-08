import random
import fractions
import unittest
import cffi

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
void *axby_make(unsigned int maxb, unsigned int maxp, int a, int x, int b, int y);
void axby_next(void *axbyp, struct point *pp, int count);
void axby_free(void *axbyp);
''')

class TestModPow(unittest.TestCase):
    def __check(self, b, e, m):
        value1 = pow(b, e, m)
        value2 = libbeal.c_modpow(b, e, m)
        self.assertEqual(value1, value2,
                "%d != %d: %d %d %d" % (value1, value2, b, e, m))

    def test_dense(self):
        for base in range(1, 200):
            for expo in range(1, 200):
                for mod in range(1, 200):
                    self.__check(base, expo, mod)

    def test_random(self):
        for _ in range(10000):
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
        for u in range(1, 100):
            for v in range(1, 100):
                self.__check(u, v)

    def test_random(self):
        for _ in range(1000):
            u = random.randint(1, 2**32-1)
            v = random.randint(1, 2**32-1)
            self.__check(u, v)

class TestCz(unittest.TestCase):
    def __check(self, maxb, maxp, mod):
        czp = libbeal.cz_make(maxb, maxp, mod)

        values = set()
        for c in xrange(1, maxb+1):
            for z in xrange(3, maxp+1):
                value1 = pow(c, z, mod)
                value2 = libbeal.cz_get(czp, c, z)
                self.assertEqual(value1, value2)
                values.add(value2)

        # assert that ever value in c^z is in the exists set
        for value in values:
            exists = libbeal.cz_exists(czp, value)
            self.assertTrue(exists)

        # iterating over all 2^32 positions in the exists set is expensive so
        # we just perform a random sampling. anything that isn't false should
        # be in the exists set we calculated above from the cz table
        for _ in xrange(10000):
            value = random.randint(0, 2**32-1)
            exists = libbeal.cz_exists(czp, value)
            if exists:
                self.assertTrue(value in values)

        libbeal.cz_free(czp)

    def test_random(self):
        for _ in xrange(10):
            maxb = random.randint(1, 100)
            maxp = random.randint(3, 100)
            mod = random.randint(1, 2**32-1)
            self.__check(maxb, maxp, mod)

    def test_specific(self):
        self.__check(1000, 1000, 4294967291)
        self.__check(1000, 1000, 4294967279)

    def test_dense(self):
        for maxb in range(1, 10):
            for maxp in range(3, 10):
                for mod in range(1, 10):
                    self.__check(maxb, maxp, mod)

class TestAxby(unittest.TestCase):
    def test_all_points(self):
        maxb = 100
        maxp = 100
        axbyp = libbeal.axby_make(maxb, maxp, 1, 3, 1, 3)
        point = ffi.new('struct point [1]')
        for a in xrange(1, maxb+1):
            for b in xrange(1, maxb+1):
                if b > a or fractions.gcd(a, b) > 1:
                    continue
                for x in xrange(3, maxp+1):
                    for y in xrange(3, maxp+1):
                        libbeal.axby_next(axbyp, point, 1)
                        self.assertEqual(a, point[0].a)
                        self.assertEqual(x, point[0].x)
                        self.assertEqual(b, point[0].b)
                        self.assertEqual(y, point[0].y)
        libbeal.axby_free(axbyp)

if __name__ == '__main__':
    unittest.main()
