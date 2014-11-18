## Beal's Conjecture

If `a^x + b^y = c^z`, where a, b, c, x, y, and z are positive integers and x, y and z are all greater than 2, then a, b, and c must have a common prime factor.

The conceptual strategy for conducting a counter-example search is to compute all possible points `(a, x, b, y, c, z)` and then evaluate the expression `a^x + b^y = c^z`. If the expression holds and the bases do not have a common prime factor, then a counter-example has been found.

The search space for this problem is very large. For instance, taking a maximum value for the bases and exponents of `1000` we end up with `1000^6` points. That number is so large that a 1GHz CPU that can do 1 billion cycles per second will take 1 billion seconds just to execute `1000^6` 1 cycle instructures. And evaluating the expression `a^x + b^y = c^z` takes far more than 1 cycle. We need to be smarter.

### Optimization 1

Since `a^x + b^y` is communative we don't have to bother testing `b^y + a^x`. This cuts down the search space by 50%. But, 50% 

Avoid recomputation

# Motivation

http://www.andrewbeal.com/andybeal/media/medialibrary/Documents/Beal-Conjecture-Prize-Increased-130603.pdf
