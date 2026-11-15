"""Single source for physical constants (invariant I-12).

Every physics module imports constants from here and only here; hand-typed
constant literals elsewhere fail test_constants_policy. Values are CODATA via
scipy.constants; the source string is recorded into every run's environment.
"""

import scipy
from scipy import constants as _sc

h = _sc.h                      # Planck constant [J s]
c = _sc.c                      # speed of light [m/s]
k_B = _sc.k                    # Boltzmann constant [J/K]
sigma_sb = _sc.sigma           # Stefan-Boltzmann constant [W m^-2 K^-4]
b_wien = _sc.Wien              # Wien displacement constant [m K]
m_e = _sc.m_e                  # electron mass [kg]
e_charge = _sc.e               # elementary charge [C]

CODATA_SOURCE = f"scipy.constants (CODATA), scipy=={scipy.__version__}"
