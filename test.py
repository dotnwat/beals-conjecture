import ctypes
import random
import fractions
import unittest

libbeal = ctypes.CDLL("./libbeal.so")

# uint64_t, uint64_t, uint32_t -> uint32_t
libbeal.c_modpow.argtypes = [ctypes.c_ulonglong,
        ctypes.c_ulonglong, ctypes.c_uint]
libbeal.c_modpow.restype = ctypes.c_uint

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

if __name__ == '__main__':
    unittest.main()
