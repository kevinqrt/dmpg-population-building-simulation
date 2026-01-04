from scipy.integrate import solve_ivp
import numpy as np
import matplotlib.pyplot as plt


# Function that defines the differential equations for the system
def model(t, z, alpha, beta, delta, gamma):
    x, y = z
    dxdt = alpha * x - beta * x * y
    dydt = delta * x * y - gamma * y
    return [dxdt, dydt]


# parameters
alpha = 1.1
beta = 0.4
delta = 0.1
gamma = 0.4

# initial condition
z0 = [10, 5]

# Time span (start, end)
t_span = [0, 50]

# Solve the ODE with the DOP853 method
sol = solve_ivp(model, t_span, z0, args=(alpha, beta, delta, gamma), method='DOP853', dense_output=True)

# Create an array of time points within the interval and evaluate the solution at those points
t = np.linspace(t_span[0], t_span[1], 500)
z = sol.sol(t)

# Plot the solution
plt.plot(t, z[0, :], 'b-', label='prey')
plt.plot(t, z[1, :], 'r--', label='predator')
plt.ylabel('population')
plt.xlabel('time')
plt.legend(loc='best')
plt.show()
plt.title('Lotka-Volterra Model')
