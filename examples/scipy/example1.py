from scipy.integrate import solve_ivp
import numpy as np
import matplotlib.pyplot as plt


# Function that returns dy/dt
def model(t, y):
    dydt = -2 * y
    return dydt


# initial condition
y0 = [1]

# time points
t_span = [0, 5]

# Solve the ODE with the DOP853 method
sol = solve_ivp(model, t_span, y0, method='RK45', dense_output=True)

# create an array of time points within the interval and evaluate the solution at those points
t = np.linspace(t_span[0], t_span[1], 300)
y = sol.sol(t)

# plot results
plt.plot(t, y[0, :])
plt.xlabel('time')
plt.ylabel('y(t)')
plt.show()
plt.title('Solution of the ODE')
