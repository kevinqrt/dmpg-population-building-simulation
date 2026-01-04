from scipy.integrate import solve_ivp
import numpy as np
import matplotlib.pyplot as plt


# Function that returns dy/dt
def model(t, y):
    dydt = -2 * y
    return dydt


# Event function that stops integration at y=0.1
def stop_event(t, y):
    return y[0] - 0.1


# The solver will stop when this event is triggered
stop_event.terminal = True

# initial condition
y0 = [1]

# time points
t_span = [0, 5]

# Solve the ODE with the DOP853 method
sol = solve_ivp(model, t_span, y0, method='DOP853', events=stop_event, dense_output=True)

# create an array of time points within the interval and evaluate the solution at those points
t = np.linspace(t_span[0], sol.t[-1], 300)  # use final time from solver
y = sol.sol(t)

# plot results
plt.plot(t, y[0, :])
plt.xlabel('time')
plt.ylabel('y(t)')
plt.title('Solution of the ODE')
plt.show()
