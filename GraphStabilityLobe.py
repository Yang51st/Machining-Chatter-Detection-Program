import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

def long_function(n,x1,x2,x3,x4,c2,c3,c4):
    return 1/(2*x1*abs(np.minimum(np.real(-(x2+c2*1j)/(n**2*1j/(x3+c3*1j)+(x4+c4*1j)*1j*n/(x3+c3*1j)+1)),np.array([0 for kk in range(len(n))]))))
    #Above is the equation from the 2021 Brecher paper. Note how some of the constants are actually complex, so extra unknowns are added.

#Points that represent the transition from chatter to stability, or vice-versa.
xD=np.array([3150.0,3100.0,3050.0,3000.0,2950.0,2800.0,2850.0,2900.0]) #Unit is spindle speed RPM.
yD=np.array([0.4289218303155231,0.4059379925944287,0.34397048564101873,0.20389099123977059,0.0641034224770947,0.056,0.052,0.06]) #Unit is depth of cut in millimetres.

popt,pcov=curve_fit(long_function,xD,yD,maxfev=900000) #Fitting a curve, with a high maxfev value to give enough time for calculation.
yFit=long_function(np.array([k for k in range(2750,3300)]),*popt) #Getting the Y values of points on the fitted curve.
plt.plot(np.array([k for k in range(2750,3300)]),yFit) #Plotting the curve fitted to the data.
plt.plot(xD,yD,"k.")
plt.show()
print(*popt) #Showing the values calculated for the unknown constants in the above equation.