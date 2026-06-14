import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# --- Carregar dados ---
raw    = np.load("variaveis_pid_raw.npz")
smooth = np.load("variaveis_pid_smooth.npz")

t_r = raw["t"];    u_r = raw["u"];    y_r = raw["y"]
t_s = smooth["t"]; u_s = smooth["u"]; y_s = smooth["y"]

setpoint = 0.2
Ts       = 0.1   # período de amostragem usado no ensaio

# --- Cálculo do erro a partir dos dados ---
e_r = setpoint - y_r
e_s = setpoint - y_s

# Erro acumulado: soma de e(k)*Ts para cada amostra k
# Equivale à integral discreta do erro pelo método rectangular
e_acumulado_r = np.cumsum(e_r) * Ts
e_acumulado_s = np.cumsum(e_s) * Ts

# --- Métricas no terminal ---
def metricas(label, t, u, y, e, e_acum, sp):
    erro_final    = sp - y[-50:].mean()
    iae           = np.sum(np.abs(e))
    ise           = np.sum(e**2)
    overshoot     = max(0.0, (y.max() - sp) / sp * 100)
    u_variacao    = np.sum(np.abs(np.diff(u)))

    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    print(f"  Setpoint                          : {sp:.4f}")
    print(f"  y final (média últimas 50 amostras): {y[-50:].mean():.4f}")
    print(f"  Erro final (sp - y_final)          : {erro_final:.4f}")
    print(f"  Overshoot                          : {overshoot:.2f}%")
    print(f"  IAE (integral do erro absoluto)    : {iae:.4f}")
    print(f"  ISE (integral do erro quadrático)  : {ise:.4f}")
    print(f"  Erro acumulado final (soma e*Ts)   : {e_acum[-1]:.4f}")
    print(f"  Variação total do actuador         : {u_variacao:.4f}")
    print(f"  u mínimo aplicado                  : {u.min():.4f}")
    print(f"  u máximo aplicado                  : {u.max():.4f}")

metricas("PID — ganhos via dy raw",    t_r, u_r, y_r, e_r, e_acumulado_r, setpoint)
metricas("PID — ganhos via dy smooth", t_s, u_s, y_s, e_s, e_acumulado_s, setpoint)

# --- Visualização ---
fig, axes = plt.subplots(4, 1, figsize=(12, 14))

ax_yr, ax_ur, ax_ys, ax_us = axes

ax_yr.plot(t_r, y_r, 'b', linewidth=0.8, label='y(t) — raw')
ax_yr.axhline(setpoint, color='r', linestyle='--', linewidth=1.0,
              label=f'setpoint = {setpoint}')
ax_yr.set_ylabel('y (normalizado)')
ax_yr.set_title('PID — ganhos via dy raw — saída')
ax_yr.legend(fontsize=8)
ax_yr.grid(True)

ax_ur.plot(t_r, u_r, 'k', linewidth=0.8, label='u(t) — raw')
ax_ur.set_ylabel('u (normalizado)')
ax_ur.set_title('PID — ganhos via dy raw — entrada')
ax_ur.legend(fontsize=8)
ax_ur.grid(True)

ax_ys.plot(t_s, y_s, 'b', linewidth=0.8, label='y(t) — smooth')
ax_ys.axhline(setpoint, color='r', linestyle='--', linewidth=1.0,
              label=f'setpoint = {setpoint}')
ax_ys.set_ylabel('y (normalizado)')
ax_ys.set_title('PID — ganhos via dy smooth — saída')
ax_ys.legend(fontsize=8)
ax_ys.grid(True)

ax_us.plot(t_s, u_s, 'k', linewidth=0.8, label='u(t) — smooth')
ax_us.set_ylabel('u (normalizado)')
ax_us.set_xlabel('Tempo [s]')
ax_us.set_title('PID — ganhos via dy smooth — entrada')
ax_us.legend(fontsize=8)
ax_us.grid(True)

plt.tight_layout()
plt.savefig("comparacao_pid.png", dpi=150)
print("\nGráfico guardado em comparacao_pid.png")
