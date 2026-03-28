#Physics Constants
g = 9.81  # Gravity (m/s²)
vertical_velocity = 0  # Vertical velocity (m/s)
rho0 = 1.225  # Air density at sea level (kg/m³)
H = 8000  # Scale height for atmosphere (m)
S = 27.87  # Wing area of F-16 (m²)
Sf = 28  # Reference area for drag
mass = 12000  # Max takeoff weight (kg)
T_max = 129000  # Max thrust of F-16 (N)
Cd0 = 0.03  # Zero-lift drag coefficient
k = 0.07  # Induced drag factor
CL0 = 0.2  # Lift coefficient at zero AoA
CL_alpha = 0.12  # Lift curve slope per degree
missile_weight = 85  # Missile weight (kg)
missile_velocity = 328  # Missile speed (m/s)
speed_penalty = 1.0  # Global speed penalty from armor

def get_air_density(y):
    return rho0 * math.exp(-y / H)

def get_lift_coefficient(AoA):
    return CL0 + CL_alpha * AoA

def get_drag_coefficient(CL):
    return Cd0 + k * CL**2

def calculate_forces(AoA, velocity, altitude, throttle):
    rho = get_air_density(altitude)
    CL = get_lift_coefficient(AoA)
    CD = get_drag_coefficient(CL)
   
    Lift = 0.5 * rho * velocity**2 * S * CL
    Drag = 0.5 * rho * velocity**2 * S * CD
    Thrust = throttle * T_max * (1 - velocity / 900) * speed_penalty
    Weight = mass * g
   
    return Lift, Drag, Thrust, Weight
