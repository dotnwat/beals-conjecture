import random
import fractions
import unittest
import os
import re
import beal

# run fast tests?
_FAST = False
if os.environ.get("FAST") == "1":
    _FAST = True

class TestModPow(unittest.TestCase):
    def __check(self, b, e, m):
        value1 = pow(b, e, m)
        value2 = beal.modpow(b, e, m)
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
        value2 = beal.gcd(u, v)
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
        cz = beal.cz(maxb, maxp, mod)

        values = set()
        for c in xrange(1, maxb+1):
            for z in xrange(3, maxp+1):
                value1 = pow(c, z, mod)
                value2 = cz.get(c, z)
                self.assertEqual(value1, value2)
                values.add(value2)
        assert len(values) > 0

        # assert that every value in c^z is set in the exists set
        for value in values:
            exists = cz.exists(value)
            self.assertTrue(exists)

        # iterating over all 2^32 positions in the exists set is expensive so
        # we just perform a random sampling. anything that isn't false should
        # be in the exists set we calculated above from the cz table
        # 10M,100M -> 1.3s,12s,
        limit = 10**6 if fast else 10**8
        for _ in xrange(limit):
            value = random.randint(0, 2**32-1)
            exists = cz.exists(value)
            if exists:
                self.assertTrue(value in values)

        cz.cleanup()

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
        for a in xrange(1, maxb+1):
            axby = beal.axby(maxb, maxp, a)
            for b in xrange(1, a+1):
                if fractions.gcd(a, b) > 1:
                    continue
                for x in xrange(3, maxp+1):
                    for y in xrange(3, maxp+1):
                        done, point = axby.next()
                        assert(not done)
                        aa, xx, bb, yy = point
                        self.assertEqual(a, aa)
                        self.assertEqual(x, xx)
                        self.assertEqual(b, bb)
                        self.assertEqual(y, yy)
            done, point = axby.next()
            assert(done)
            axby.cleanup()

class TestSearch(unittest.TestCase):
    PRIMES = [4294967291, 4294967279]

    def __get_gold(self, maxb, maxp):
        results = set()
        regex = re.compile(r"(\d+)\^(\d+) \+ (\d+)\^(\d+)")
        filename = "gold/danvk_%dx%d.dat" % (maxb, maxp)
        with open(filename) as f:
            for line in f.readlines():
                m = regex.match(line)
                if not m:
                    continue
                a = int(m.group(1))
                x = int(m.group(2))
                b = int(m.group(3))
                y = int(m.group(4))
                results.add((a, x, b, y))
        return results

    def __check_gold(self, maxb, maxp, primes):
        results = set()
        search = beal.search(maxb, maxp, primes)
        for a in range(1, maxb+1):
            hits = search.search(a)
            results.update(set(hits))
        self.assertEqual(results, self.__get_gold(maxb, maxp))

    def test_100x100(self):
        self.__check_gold(100, 100, self.PRIMES)

    def test_300x300(self):
        self.__check_gold(300, 300, self.PRIMES)

    def test_500x500(self):
        self.__check_gold(500, 500, self.PRIMES)

    def test_1000x1000(self):
        self.__check_gold(1000, 1000, self.PRIMES)

if __name__ == '__main__':
    unittest.main()
