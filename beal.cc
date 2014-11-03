#include <stdint.h>
#include <assert.h>
#include <vector>

/*
 * http://en.wikipedia.org/wiki/Modular_exponentiation
 */
static inline uint32_t modpow(uint64_t base, uint64_t exponent, uint32_t mod)
{
  uint64_t result = 1;

  base = base % mod;
  while (exponent > 0) {
    if (exponent % 2 == 1)
      result = (result * base) % mod;
    exponent = exponent >> 1;
    base = (base * base) % mod;
  }

  assert(result <= (((1ULL) << 32)-1));
  return result;
}

/*
 * http://en.wikipedia.org/wiki/Binary_GCD_algorithm
 */
static inline unsigned int gcd(unsigned int u, unsigned int v)
{
  int shift;

  /* GCD(0,v) == v; GCD(u,0) == u, GCD(0,0) == 0 */
  if (u == 0)
    return v;
  if (v == 0)
    return u;

  /* Let shift := lg K, where K is the greatest power of 2
        dividing both u and v. */
  for (shift = 0; ((u | v) & 1) == 0; ++shift) {
         u >>= 1;
         v >>= 1;
  }

  while ((u & 1) == 0)
    u >>= 1;

  /* From here on, u is always odd. */
  do {
       /* remove all factors of 2 in v -- they are not common */
       /*   note: v is not zero, so while will terminate */
       while ((v & 1) == 0)  /* Loop X */
           v >>= 1;

       /* Now u and v are both odd. Swap if necessary so u <= v,
          then set v = v - u (which is even). For bignums, the
          swapping is just pointer movement, and the subtraction
          can be done in-place. */
       if (u > v) {
         unsigned int t = v; v = u; u = t;
       }  // Swap u and v.
       v = v - u;                       // Here v >= u.
     } while (v != 0);

  /* restore common factors of 2 */
  return u << shift;
}

class cz {
 public:
  cz(unsigned int maxb, unsigned int maxp, uint32_t mod) {
    assert(maxb > 0);
    assert(maxp > 2);
    assert(mod > 0);
    vals_.resize(maxb+1);
    exists_.resize(1ULL<<32);
    for (unsigned int c = 1; c <= maxb; c++) {
      vals_[c].resize(maxp+1);
      for (unsigned int z = 3; z <= maxp; z++) {
        uint32_t val = modpow(c, z, mod);
        vals_[c][z] = val;
        exists_[val] = true;
      }
    }
  }

  inline uint32_t get(int c, int z) const {
    assert(c > 0);
    assert(z > 2);
    return vals_[c][z];
  }

  inline bool exists(uint32_t val) const {
    return exists_[val];
  }

 private:
  std::vector<std::vector<uint32_t> > vals_;
  std::vector<bool> exists_;
};


extern "C" {

  /*
   * Access to routines for testing
   */
  uint32_t c_modpow(uint64_t base, uint64_t exponent, uint32_t mod) {
    return modpow(base, exponent, mod);
  }

  unsigned int c_gcd(unsigned int u, unsigned int v) {
    return gcd(u, v);
  }

  void *cz_make(unsigned int maxb, unsigned int maxp, uint32_t mod) {
    cz *p = new cz(maxb, maxp, mod);
    return (void*)p;
  }

  void cz_free(void *czp) {
    cz *p = (cz*)czp;
    delete p;
  }

  uint32_t cz_get(void *czp, int c, int z) {
    cz *p = (cz*)czp;
    return p->get(c, z);
  }

  bool cz_exists(void *czp, uint32_t val) {
    cz *p = (cz*)czp;
    return p->exists(val);
  }
}
