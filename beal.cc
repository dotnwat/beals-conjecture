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

/*
 * Utility over c^z space for a particular mod value.
 */
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
    mod_ = mod;
  }

  inline uint32_t get(int c, int z) const {
    assert(c > 0);
    assert(z > 2);
    return vals_[c][z];
  }

  inline bool exists(uint32_t val) const {
    return exists_[val];
  }

  inline uint32_t mod() const {
    return mod_;
  }

 private:
  std::vector<std::vector<uint32_t> > vals_;
  std::vector<bool> exists_;
  uint32_t mod_;
};

/*
 * Iterator over (a, x, b, y) space.
 *
 * The starting point is a value for the "a" dimension. All points will be
 * generated and the normal trimming optimizations (b <= a, gcd) will be
 * applied.
 *
 * After initializing the class call next() next until the output parameter is
 * false. When false is returned the corresponding point should be discarded.
 */
class axby {
 public:
  struct point {
    point(int a, int x, int b, int y) :
      a(a), x(x), b(b), y(y)
    {}

    int a, x, b, y;
  };

  axby(int maxb, int maxp, int a) :
    maxb_(maxb), maxp_(maxp), p_(a, 3, 1, 3), a_dim_(a)
  {
    assert(maxb > 0);
    assert(maxp > 2);
    assert(p_.a > 0);
    assert(p_.x == 3);
    assert(p_.b == 1);
    assert(p_.y == 3);
    p_.y--; // first next() call will be starting point
  }

  inline point& next(bool *done) {
    assert(p_.a == a_dim_);
    if (++p_.y > maxp_) {
      p_.y = 3;
      if (++p_.x > maxp_) {
        p_.x = 3;
        p_.b++;
        for (;;) {
          if (p_.b > p_.a) {

            // this is where b rolls over. when generating the entire space of
            // points this is the point we would increment "a". For example:
            //
            //   p_.b = 1;
            //   if (++p_.a > maxb_) {
            //     *done = true;
            //     return p_;
            //   }
            //
            // Since we only want to iterate over the space for a given "a"
            // value this is the point we return `done = true` to the caller.

            // bump p_.a so we can assert on its uniqueness
            p_.a++;
            *done = true;
            return p_;

          } else if (gcd(p_.a, p_.b) > 1) {
            p_.b++;
          } else
            break;
        }
      }
    }

    *done = false;
    return p_;
  }

 private:
  int maxb_;
  int maxp_;
  struct point p_;
  int a_dim_;
};

class work {
 public:
  work(int maxb, int maxp, uint32_t *primes, size_t nprimes) :
    maxb_(maxb), maxp_(maxp) {
      for (size_t i = 0; i < nprimes; i++) {
        std::cout << primes[i] << std::endl;
        czs_.push_back(new cz(maxb, maxp, primes[i]));
      }
  }

  ~work() {
    for (size_t i = 0; i < czs_.size(); i++)
      delete czs_[i];
  }

  void dowork(int a) {
    bool done;
    axby pts(maxb_, maxp_, a);
    axby::point& pt = pts.next(&done);
    while (!done) {
      std::vector<cz*>::const_iterator it = czs_.begin();
      for (; it != czs_.end(); it++) {
        cz *czp = *it;
        uint64_t tmp = czp->get(pt.a, pt.x) + czp->get(pt.b, pt.y);
        uint32_t val = tmp % czp->mod();
        if (!czp->exists(val))
          break;
      }

      // candidate?
      if (it == czs_.end())
        std::cout << pt.a << " " << pt.x << " " << pt.b << " " << pt.y << std::endl;

      pt = pts.next(&done);
    }
  }

 private:
  int maxb_;
  int maxp_;
  std::vector<cz*> czs_;
};

/*
 * C-linkage interface for testing because it is super convenient to
 * coordinate all the tests from Python. Used via cffi or ctypes.
 */
extern "C" {
  void *work_make(unsigned int maxb, unsigned int maxp, uint32_t *primes, size_t nprimes) {
    work *p = new work(maxb, maxp, primes, nprimes);
    return (void*)p;
  }

  void work_work(void *workp, int a) {
    work *p = (work*)workp;
    p->dowork(a);
  }

  void work_free(void *workp) {
    work *p = (work*)workp;
    delete p;
  }

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

  void *axby_make(unsigned int maxb, unsigned int maxp, int a) {
    axby *p = new axby(maxb, maxp, a);
    return (void*)p;
  }

  /* if done, the returned point is invalid. */
  bool axby_next(void *axbyp, axby::point *pp) {
    axby *p = (axby*)axbyp;
    bool done;
    axby::point& pt = p->next(&done);
    pp->a = pt.a;
    pp->x = pt.x;
    pp->b = pt.b;
    pp->y = pt.y;
    return done;
  }

  void axby_free(void *axbyp) {
    axby *p = (axby*)axbyp;
    delete p;
  }
}
