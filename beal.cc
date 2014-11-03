#include <stdint.h>
#include <assert.h>

/*
 * http://en.wikipedia.org/wiki/Modular_exponentiation
 */
static inline uint32_t modpow(uint64_t base, uint64_t exponent, uint32_t mod)
{
  uint64_t result = 1;

  while (exponent > 0) {
    if (exponent % 2 == 1)
      result = (result * base) % mod;
    exponent = exponent >> 1;
    base = (base * base) % mod;
  }

  assert(result <= (((1ULL) << 32)-1));
  return result;
}

extern "C" {

  /*
   * Access to routines for testing
   */
  uint32_t c_modpow(uint64_t base, uint64_t exponent, uint32_t mod) {
    return modpow(base, exponent, mod);
  }
}
