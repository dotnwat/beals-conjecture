# Distributed search for a counterexample to Beal's Conjecture!

Beal's Conjecture says that if `a^x + b^y = c^z`, where a, b, c, x, y, and z are positive integers and x, y and z are all greater than 2, then a, b, and c must have a common prime factor.

There is a monetary prize offered by Andrew Beal for a proof or counterexample to the conjecture. More information about the prize can be found here http://www.ams.org/profession/prizes-awards/ams-supported/beal-prize. This project aims to expand the size of the counterexample search space covered compared to previous efforts by using a distributed search strategy.

#### Previous Efforts

* http://norvig.com/beal.html 
* http://www.danvk.org/wp/beals-conjecture/

#### Problem Overview

The conceptual strategy for conducting a counterexample search is to compute all possible points `(a, x, b, y, c, z)` and then evaluate the expression `a^x + b^y = c^z`. If the expression holds and the bases do not have a common prime factor, then a counterexample has been found.

The core challenge behind a counterexample search strategy is dealing with the enormous size of the space being examined. For instance, taking a maximum value for the bases and exponents of `1000` we end up with `1000^6` points. That number is so large that a 1GHz CPU that can do 1 billion cycles per second will take 1 billion seconds just to execute `1000^6` 1 cycle instructions. Evaluating the expression `a^x + b^y = c^z` takes far more than 1 cycle, so we need to be smart about the search.

First we will describe the simplest algorithm for conducting a counterexample search, and then iteratively refine it with  various optimizations. Then we will show how scaling this simple algorithm hits a wall very quickly, and then describe additional optimizations that let us expand the search space past what is possible with the simple algorithm. The optimizations and search techniques described have all been considered in previous efforts. Finally we'll describe our new implementation that distributes the problem allowing us to further scale the problem sizes being considered.

## Generation 1 Algorithm

The following is a naive algorithm for conducting a search that computes every combination of the points `(a, x, b, y, c, z)` and then checks if the point represents a counterexample:

```python
for a in range(1, max_base+1):
    for b in range(1, max_base+1):
        for x in range(3, max_pow+1):
            for y in range(3, max_pow+1):
                for c in range(1, max_pow+1):
                    for z in range(3, max_pow+1):
                        check(a, x, b, y, c, z)
```

A candidate verison of the `check` function might do something like the following:

```python
def check(a, x, b, y, c, z):
    axby = pow(a, x) + pow(b, y)
    cz = pow(c, z)
    if axby == cz and gcd(a, b) == 1 and gcd(a, c) == 1 and gcd(b, c) == 1:
        print "found counterexample:", a, x, b, y, c, z
```

I ran this algorithm for 85 minutes. In that period of time `859,796,767` points were examined. Considering the size of the state space with maximum base and exponent values of `1000`, that is approximately `0.0000000859796767 %` of the total space covered. In reality it will probably run much slower than this short experiment doesn't include the very large exponents that take a lot of effort to compute. This test was written in Python, but even when written in optimized C, this strategy will simply not scale with search spaces this size. In order to make progress we need to cut down on the amount of work we are doing.

### Optimization 1

Since `a^x + b^y` is communative we don't have to bother also testing `b^y + a^x`. This can be incorporated into the algorithm above by adjusting the upper bound of the values assigned to `b`:

```python
for a in range(1, max_base+1):
    for b in range(1, a+1):
        ...
```

This filter reduces by 50% the number of points that must be considered. The problem is that the search space is so large that even with a 50% reduction in size it is still much too large. But we certainly want to use any optimizations we can find.

### Optimization 2

Since we only care about counterexamples we don't need to check any points where the bases have a common prime. This means that when iterating over the points in the space we can skip all points for which any two of the bases (e.g. `a` and `b`) have a common prime factor.

```python
for a in range(1, max_base+1):
    for b in range(1, a+1):
        if fractions.gcd(a, b) > 1:
            continue
        ...
```

This is actually a pretty nice optimization. Even though computing `gcd` isn't cheap, we only have to do it roughly `max_base * (max_base + 1) / 2` times and what we get in return is the ability to completely skip the rest of the nested for loops for that combination of `(a, b)` values.

### Optimization 3

Notice above that for each left-hand-side value that is computed (the outer four for loops) all of the possible right-hand-side values are re-computed. Since the complexity of the right-hand-side is relatively small, we can pre-compute all possible `c^z` values and *search* for the match using a data structure such as a hash table. The following is a revised version of the above the previous algorithm that avoids the recomputation of all `c^z` values.

```python
cz_values = defaultdict(lambda: [])

for c in range(1, max_base+1):
    for z in range(3, max_pow+1):
        value = pow(c, z)
        cz[value].append((c, z))

for a in range(1, max_base+1):
    for b in range(1, a+1):
        if gcd(a, b) > 1:
            continue
        for x in range(3, max_pow+1):
            for y in range(3, max_pow+1):
                check(a, x, b, y)
```

And now check avoids computing c^z and instead looks it up.

```python
def check(a, x, b, y):
    axby = pow(a, x) + pow(b, y)
    for c, z in cz_values[axby]:
        if gcd(a, b) == 1 and gcd(a, c) == 1 and gcd(b, c) == 1:
            print "counterexample found:", a, x, b, y, c, z
```

### Optimization 4

We can re-use the computation of c^z by saving the results of computing the c^z values for searching

```python
cz_values = defaultdict(lambda: [])
powers = defaultdict(lambda: {})

for c in range(1, max_base+1):
    for z in range(3, max_pow+1):
        value = pow(c, z)
        cz[value].append((c, z))
        powers[c][z] = value
```

Then

```python
for a, x, b, y in axby_space(max_base, max_pow):
    axby = powers[a][x] + powers[b][y]
    ...
```

Now we are getting somewhere. This is actually a simplified version of the approach used by Peter Norvig. His results from several years ago computed several different ranges (100x100 is done in 3minutes). But new methods are needed to go beyond what he is doing (e.g. 1000x100 is 19 hours and 100x10000 took 39 days).

This is pretty good, really. We can construct a parallel version by breaking up the for loop and having worker nodes evaluate different disjoint partitions of the space.

The major problem with this is the cost in size to maintain the index of infinite percision numbers with a lot digits, as well as the huge number of cycles needed to make comparisons between these large integers.

# Open Questions

* Are there other ways that the state space can be trimmed?
* Are there classes of points that are more interesting to test (e.g. large exponents)?
* Are there methods for making the modulo-based filtering more effective (e.g. larger primes)
* What improvements can we get by using GPU-based acceleration (e.g. CUDA or OpenCL)?
* Can we make searching the `c^z` space even faster by taking advantage of cache locality?
