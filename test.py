import numpy as np
from scipy import interpolate
from matplotlib import pyplot as plt

T2_list = np.arange(3, 350, 0.1)
R2_list = np.exp(6.85541945) * np.exp(0.8522265 / T2_list ** 0.5)
T2_interpolator = interpolate.interp1d(R2_list, T2_list, fill_value="extrapolate")
print(T2_interpolator(997.3))
plt.plot(T2_list, R2_list)
plt.show()
