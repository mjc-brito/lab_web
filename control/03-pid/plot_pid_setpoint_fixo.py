import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# --- Carregar dados ---
data = np.load("20260615-variaveis_pid_setpoint_fixo.npz")
t    = data["t"]
u    = data["u"]
y    = data["y"]

setpoint = data["setpoint"]
Ts       = data["Ts"]

# --- Métricas ---
e                 = setpoint - y
squared_error_sum = np.sum(e**2) * Ts
e_accumulated     = np.cumsum(e) * Ts
y_final           = y[-50:].mean()
final_error       = abs(setpoint - y_final)
overshoot         = max(0.0, (y.max() - setpoint) / setpoint * 100)
actuator_variation = np.sum(np.abs(np.diff(u)))

print(f"setpoint                    : {setpoint:.4f}")
print(f"y final (média últimas 50)  : {y_final:.4f}")
print(f"erro final                  : {final_error:.4f}")
print(f"overshoot                   : {overshoot:.2f}%")
print(f"squared error sum (ISE)     : {squared_error_sum:.6f}")
print(f"erro acumulado final        : {e_accumulated[-1]:.6f}")
print(f"variação total do actuador  : {actuator_variation:.4f}")
print(f"u mínimo                    : {u.min():.4f}")
print(f"u máximo                    : {u.max():.4f}")

# --- Visualização ---
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 9))

ax1.plot(t, y, 'b', linewidth=0.8, label='y(t)')
ax1.axhline(setpoint, color='r', linestyle='--', linewidth=1.0,
            label=f'setpoint = {setpoint}')
ax1.set_ylabel('y (normalizado)')
ax1.set_title(f'PID setpoint fixo — soma do erro quadratico={squared_error_sum:.4f}  '
              f'overshoot={overshoot:.1f}%')
ax1.legend(fontsize=8)
ax1.grid(True)

ax2.plot(t, u, 'k', linewidth=0.8, label='u(t)')
ax2.set_ylabel('u (normalizado)')
ax2.legend(fontsize=8)
ax2.grid(True)

plt.tight_layout()
plt.savefig("img_pid_setpoint_fixo.png", dpi=150)
print("\nGráfico guardado em img_pid_setpoint_fixo.png")