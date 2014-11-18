## Beal's Conjecture

If `a^x + b^y = c^z`, where a, b, c, x, y, and z are positive integers and x, y and z are all greater than 2, then a, b, and c must have a common prime factor.

The conceptual strategy for conducting a counterexample search is to compute all possible points `(a, x, b, y, c, z)` and then evaluate the expression `a^x + b^y = c^z`. If the expression holds and the bases do not have a common prime factor, then a counterexample has been found.

The search space for this problem is very large. For instance, taking a maximum value for the bases and exponents of `1000` we end up with `1000^6` points. That number is so large that a 1GHz CPU that can do 1 billion cycles per second will take 1 billion seconds just to execute `1000^6` 1 cycle instructures. And evaluating the expression `a^x + b^y = c^z` takes far more than 1 cycle. We need to be smarter.

### Optimization 1

Since `a^x + b^y` is communative we don't have to bother testing `b^y + a^x`.

### Optimization 2

Since we only care about counterexamples we don't need to check any points where the bases have a common prime. This means that when iterating over the points in the space we can skip points where any two of the bases (e.g. `a` and `b`) have a common prime factor.

## Naive Algorithm 1

The following Python psuedo-code shows a basic example of how to iterate over the space.

    for a in range(1, max_base+1):
      for b in range(1, a+1):
        if gcd(a, b) > 1:
          continue
        for x in range(3, max_pow+1):
          for y in range(3, max_pow+1):
            for c in range(1, max_pow+1):
              for z in range(3, max_pow+1):
                check(a, x, b, y, c, z)

A candidate verison of the `check` function might do something like the following:

    def check(a, x, b, y, c, z):
      axby = pow(a, x) + pow(b, y)
        cz = pow(c, z)
      if axby == cz and gcd(a, b) == 1 and gcd(b, c) == 1:
        print "found counterexample:", a, x, b, y, c, z

Notice above that for each left-hand-side value that is computed (the outer four for loops) all of the possible right-hand-side values are re-computed. Since the complexity of the right-hand-side is relatively small, we can pre-compute all possible `c^z` values and *search* for the match rather than computing all of the possible values.


We can use memory to pre-compute the c^z values and search for them rather than computing them.

Avoid recomputation

# Motivation

http://www.andrewbeal.com/andybeal/media/medialibrary/Documents/Beal-Conjecture-Prize-Increased-130603.pdf
