import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# --- Carregar dados ---
# O ficheiro contém todas as variáveis do namespace do sandbox
data = np.load("20260615-variaveis_pid_setpoint_variavel.npz", allow_pickle=True)

t   = data["t"]
u   = data["u"]
y   = data["y"]
sp  = data["sp"]
Ts  = float(data["Ts"])
Kp  = float(data["Kp"])
Ki  = float(data["Ki"])
Kd  = float(data["Kd"])

# levels_sp foi definido no sandbox como lista de tuplos —
# reconstruído a partir de sp detectando as mudanças de valor
# np.where detecta os índices onde sp muda de valor
change_indices = np.where(np.diff(sp) != 0)[0] + 1
segment_starts = np.concatenate([[0], change_indices])
segment_ends   = np.concatenate([change_indices, [len(sp)]])

segments = []
for inicio, fim in zip(segment_starts, segment_ends):
    sp_val = sp[inicio]
    segments.append((float(sp_val), int(inicio), int(fim)))

# --- Métricas globais ---
e                       = sp - y
squared_error_sum_total = np.sum(e**2) * Ts
e_accumulated           = np.cumsum(e) * Ts
actuator_variation      = np.sum(np.abs(np.diff(u)))

print(f"Kp={Kp:.6f}  Ki={Ki:.6f}  Kd={Kd:.6f}  Ts={Ts}")
print()
print(f"squared error sum total (ISE) : {squared_error_sum_total:.6f}")
print(f"erro acumulado final          : {e_accumulated[-1]:.6f}")
print(f"variação total do actuador    : {actuator_variation:.4f}")
print(f"u mínimo                      : {u.min():.4f}")
print(f"u máximo                      : {u.max():.4f}")
print()

# --- Métricas por segmento ---
for sp_val, inicio, fim in segments:
    y_seg                 = y[inicio:fim]
    sp_seg                = sp[inicio:fim]
    e_seg                 = sp_seg - y_seg
    squared_error_sum_seg = np.sum(e_seg**2) * Ts
    y_final_seg           = y_seg[-10:].mean()
    final_error_seg       = abs(sp_val - y_final_seg)
    overshoot_seg         = max(0.0, (y_seg.max() - sp_val) / sp_val * 100)
    dur_seg               = (fim - inicio) * Ts
    print(f"  setpoint={sp_val:.2f}  dur={dur_seg:.1f}s → "
          f"y final (média últimas 10): {y_final_seg:.4f}  "
          f"erro: {final_error_seg:.4f}  "
          f"overshoot: {overshoot_seg:.1f}%  "
          f"squared error sum (ISE): {squared_error_sum_seg:.6f}")

# --- Visualização ---
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 9))

ax1.plot(t, y, 'b', linewidth=0.8, label='y(t)')
ax1.plot(t, sp, 'r--', linewidth=1.0, label='setpoint(t)')
ax1.set_ylabel('y (normalizado)')
ax1.set_title(f'PID setpoint variável — Kp={Kp:.4f}  Ki={Ki:.4f}  Kd={Kd:.4f}  '
              f'soma do erro quadrático={squared_error_sum_total:.4f}')
ax1.legend(fontsize=8)
ax1.grid(True)

ax2.plot(t, u, 'k', linewidth=0.8, label='u(t)')
ax2.set_ylabel('u (normalizado)')
ax2.legend(fontsize=8)
ax2.grid(True)

# Linhas verticais e anotações nos inícios de segmento
for sp_val, inicio, fim in segments:
    for ax in (ax1, ax2):
        ax.axvline(t[inicio], color='gray', linestyle=':', linewidth=0.8)
    ax1.annotate(f'sp={sp_val:.2f}',
                 xy=(t[inicio], sp_val),
                 xytext=(t[inicio] + 0.5, sp_val + 0.01),
                 fontsize=7, color='r')

plt.tight_layout()
plt.savefig("img_pid_setpoint_variavel.png", dpi=150)
print("\nGráfico guardado em img_pid_setpoint_variavel.png")