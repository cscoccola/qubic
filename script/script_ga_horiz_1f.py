from __future__ import division

import healpy as hp
import matplotlib.pyplot as mp
import numpy as np

from pyoperators import pcg, DiagonalOperator, UnpackOperator
from pysimulators import SphericalEquatorial2GalacticOperator
from pysimulators.noises import _gaussian_psd_1f
from qubic import QubicAcquisition, QubicInstrument, create_sweeping_pointings

qubic = QubicInstrument('monochromatic,nopol', kmax=2)
input_map = hp.read_map('test/data/syn256.fits')

# pointing
racenter = 0.0
deccenter = -57.0
angspeed = 1  # deg/sec
delta_az = 15.
angspeed_psi = 0.1
maxpsi = 45.
nsweeps_el = 300
duration = 24   # hours
ts = 20         # seconds
pointings = create_sweeping_pointings(
    [racenter, deccenter], duration, ts, angspeed, delta_az, nsweeps_el,
    angspeed_psi, maxpsi)

# configure observation
obs = QubicAcquisition(qubic, pointings)
C = obs.get_convolution_peak_operator()
P = obs.get_projection_peak_operator()
H = P * C

# produce the Time-Ordered data
tod = H(input_map)

# noise
white = 10
alpha = 1
fknee = 0.025
psd = _gaussian_psd_1f(len(obs.pointing), sigma=white, fknee=fknee,
                       fslope=alpha, sampling_frequency=1/ts)
invntt = obs.get_invntt_operator(sigma=white, fknee=fknee, fslope=alpha,
                                 sampling_frequency=1/ts, ncorr=10)
noise = obs.get_noise(sigma=white, fknee=fknee, fslope=alpha,
                      sampling_frequency=1/ts)

# map-making
coverage = P.pT1()
mask = coverage > 10
P.restrict(mask)
unpack = UnpackOperator(mask)

# map without covariance matrix
solution1 = pcg(P.T * P, P.T(tod + noise),
                M=DiagonalOperator(1/coverage[mask]), disp=True)
output_map1 = unpack(solution1['x'])

# map with covariance matrix
solution2 = pcg(P.T * invntt * P, (P.T * invntt)(tod + noise),
                M=DiagonalOperator(1/coverage[mask]), disp=True)
output_map2 = unpack(solution2['x'])

e2g = SphericalEquatorial2GalacticOperator(degrees=True)
center = e2g([racenter, deccenter])


def display(x, title):
    x = x.copy()
    x[~mask] = np.nan
    hp.gnomview(x, rot=center, reso=5, xsize=600, min=-200, max=200,
                title=title)

display(C(input_map), 'Original convolved map')
#hp.projplot(np.radians(pointings[..., 0]), np.radians(pointings[..., 1]))
display(output_map1, 'Reconstructed map no invntt')
display(output_map2, 'Reconstructed map with invntt')
display(coverage, 'Coverage')

mp.show()
