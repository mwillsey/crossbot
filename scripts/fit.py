import numpy as np
import scipy.stats as stats
import pylab as pl

# times is a files with one time in seconds on each line
h = np.sort(np.loadtxt('times'))

# pick any of the distributions in scipy.stats
# it looked like lognormal to me
dist = stats.lognorm

fitargs = dist.fit(h)
print(fitargs)

pdf = dist.pdf(h, *fitargs)
pl.plot(h, pdf, '-o')
pl.hist(h, bins=50, normed=1)
pl.show()
