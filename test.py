import ctypes
import random
import fractions

libbeal = ctypes.CDLL("./libbeal.so")

# test modpow with dense range
for base in range(1, 200):
    for expo in range(1, 200):
        for mod in range(1, 200):
            val = pow(base, expo, mod)
            val2 = libbeal.c_modpow(base, expo, mod)
            assert val == val2

# test modpow with random values
for _ in range(1000):
    base = random.randint(1, 2**64-1)
    expo = random.randint(1, 2**64-1)
    mod = random.randint(1, 2**32-1)
    val = pow(base, expo, mod)
    val2 = libbeal.c_modpow(base, expo, mod)
    assert val == val

# test gcd with dense range
for u in range(1, 100):
    for v in range(1, 100):
        val = fractions.gcd(u, v)
        val2 = libbeal.c_gcd(u, v)
        assert val == val2

# test gcd with random values
for _ in range(1000):
    u = random.randint(1, 2**32-1)
    v = random.randint(1, 2**32-1)
    val = fractions.gcd(u, v)
    val2 = libbeal.c_gcd(u, v)
    assert val == val2
