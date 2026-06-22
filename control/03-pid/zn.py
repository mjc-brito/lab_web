import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# --- Carregar ---
data   = np.load("../02-step_response/uyt2.npz")
t_full = data["t"]
u_full = data["u"]
y_full = data["y"]

# --- Recorte ---
indices_degrau = np.where(u_full == 1.0)[0]
idx_inicio     = indices_degrau[0]
idx_fim        = indices_degrau[-1]

t = t_full[idx_inicio - 1 : idx_fim + 1]
u = u_full[idx_inicio - 1 : idx_fim + 1]
y = y_full[idx_inicio - 1 : idx_fim + 1]
t = t - t[0]

assert u[0] == 0.0 and u[1] == 1.0 and u[-1] == 1.0, "Recorte incorreto"

# --- K ---
u_step    = u[1]
y_repouso = y_full[:idx_inicio].mean()
y_final   = y[-50:].mean()
K         = (y_final - y_repouso) / u_step

# --- Derivada e suavização ---
dy        = np.gradient(y, t)
N_smooth  = 10
kernel    = np.ones(N_smooth) / N_smooth
dy_smooth = np.convolve(dy, kernel, mode='same')

# --- Ponto de inflexão com dy_smooth ---
idx_inf_smooth_rel = np.argmax(dy_smooth[1:])
idx_inf_smooth     = idx_inf_smooth_rel + 1
t_inf_smooth = t[idx_inf_smooth]
y_inf_smooth = y[idx_inf_smooth]
slope_smooth = dy_smooth[idx_inf_smooth]

# --- Ponto de inflexão com dy raw ---
idx_inf_raw_rel = np.argmax(dy[1:])
idx_inf_raw     = idx_inf_raw_rel + 1
t_inf_raw = t[idx_inf_raw]
y_inf_raw = y[idx_inf_raw]
slope_raw = dy[idx_inf_raw]

# --- L e T com dy_smooth ---
t_L_s = t_inf_smooth - (y_inf_smooth - y_repouso) / slope_smooth
t_T_s = t_inf_smooth + (y_final - y_inf_smooth)   / slope_smooth
L_s   = t_L_s
T_s   = t_T_s - t_L_s

# --- L e T com dy raw ---
t_L_r = t_inf_raw - (y_inf_raw - y_repouso) / slope_raw
t_T_r = t_inf_raw + (y_final - y_inf_raw)   / slope_raw
L_r   = t_L_r
T_r   = t_T_r - t_L_r

# --- Ganhos Z-N pelo 1.º método ---
# Referência: Paulo Gil p.5, tabela "Método da curva de reacção"
#   Kp = 1.2 * T/L
#   Ki = Kp / Ti  com Ti = 2*L
#   Kd = Kp * Td  com Td = 0.5*L

def zn_gains(L, T):
    Kp = 1.2 * T / L
    Ti = 2.0 * L
    Td = 0.5 * L
    Ki = Kp / Ti
    Kd = Kp * Td
    return Kp, Ki, Kd

Kp_s, Ki_s, Kd_s = zn_gains(L_s, T_s)
Kp_r, Ki_r, Kd_r = zn_gains(L_r, T_r)

# --- Comparação no terminal ---
print(f"\n{'':30s} {'dy_smooth':>12s} {'dy (raw)':>12s}")
print(f"{'-'*54}")
print(f"{'slope':30s} {slope_smooth:>12.6f} {slope_raw:>12.6f}")
print(f"{'t_inf [s]':30s} {t_inf_smooth:>12.4f} {t_inf_raw:>12.4f}")
print(f"{'L [s]':30s} {L_s:>12.4f} {L_r:>12.4f}")
print(f"{'T [s]':30s} {T_s:>12.4f} {T_r:>12.4f}")
print(f"{'K':30s} {K:>12.4f} {K:>12.4f}")
print(f"{'-'*54}")
print(f"{'Kp':30s} {Kp_s:>12.4f} {Kp_r:>12.4f}")
print(f"{'Ki':30s} {Ki_s:>12.4f} {Ki_r:>12.4f}")
print(f"{'Kd':30s} {Kd_s:>12.4f} {Kd_r:>12.4f}")

# --- Guardar resultados em ficheiro txt ---
with open("zn_gains.txt", "w") as f:
    f.write("SINTONIZAÇÃO PID — MÉTODO DA CURVA DE REACÇÃO (ZIEGLER-NICHOLS, 1.º MÉTODO)\n")
    f.write("Referência: Paulo Gil, Implementação de Controladores PID, p.5\n")
    f.write("            Ogata, Engenharia de Controle Moderno, Cap.8 p.523\n")
    f.write("Dados de entrada: ../02-step_response/uyt2.npz\n")
    f.write("\n")
    f.write("=" * 60 + "\n")
    f.write("PARÂMETROS DO PROCESSO IDENTIFICADOS\n")
    f.write("=" * 60 + "\n")
    f.write(f"K  = {K:.6f}  (ganho estático: variação normalizada de saída\n")
    f.write(f"                por variação normalizada de entrada)\n")
    f.write("\n")
    f.write("Dois conjuntos de L e T foram calculados:\n")
    f.write("  - 'suavizado': derivada de y suavizada por média deslizante\n")
    f.write(f"    (janela de {N_smooth} amostras = {N_smooth * 0.1:.1f}s), mais robusto ao ruído\n")
    f.write("  - 'raw': derivada de y sem suavização, sensível a spikes de ruído\n")
    f.write("\n")
    f.write(f"{'Parâmetro':<35} {'suavizado':>12} {'raw':>12}\n")
    f.write(f"{'-'*59}\n")
    f.write(f"{'declive da tangente no ponto de inflexão':<35} {slope_smooth:>12.6f} {slope_raw:>12.6f}\n")
    f.write(f"{'t_inf: instante do ponto de inflexão [s]':<35} {t_inf_smooth:>12.4f} {t_inf_raw:>12.4f}\n")
    f.write(f"{'L: atraso do sistema [s]':<35} {L_s:>12.4f} {L_r:>12.4f}\n")
    f.write(f"{'T: constante de tempo do sistema [s]':<35} {T_s:>12.4f} {T_r:>12.4f}\n")
    f.write("\n")
    f.write("=" * 60 + "\n")
    f.write("GANHOS DO CONTROLADOR PID (ZIEGLER-NICHOLS, 1.º MÉTODO)\n")
    f.write("=" * 60 + "\n")
    f.write("Fórmulas aplicadas (Paulo Gil p.5, tabela PID):\n")
    f.write("  Kp = 1.2 * T / L\n")
    f.write("  Ti = 2 * L        (tempo integral)\n")
    f.write("  Td = 0.5 * L      (tempo derivativo)\n")
    f.write("  Ki = Kp / Ti      (ganho integral, usado na equação às diferenças)\n")
    f.write("  Kd = Kp * Td      (ganho derivativo, usado na equação às diferenças)\n")
    f.write("\n")
    f.write("Equação às diferenças do controlador (Paulo Gil p.7):\n")
    f.write("  u(k) = u(k-1)\n")
    f.write("       + Kp * (e(k) - e(k-1))\n")
    f.write("       + Ki * Ts * (e(k) + e(k-1)) / 2\n")
    f.write("       + Kd / Ts * (e(k) - 2*e(k-1) + e(k-2))\n")
    f.write("\n")
    f.write(f"{'Ganho':<35} {'suavizado':>12} {'raw':>12}\n")
    f.write(f"{'-'*59}\n")
    f.write(f"{'Kp (ganho proporcional)':<35} {Kp_s:>12.6f} {Kp_r:>12.6f}\n")
    f.write(f"{'Ki (ganho integral)':<35} {Ki_s:>12.6f} {Ki_r:>12.6f}\n")
    f.write(f"{'Kd (ganho derivativo)':<35} {Kd_s:>12.6f} {Kd_r:>12.6f}\n")
    f.write("\n")
    f.write("=" * 60 + "\n")
    f.write("RECOMENDAÇÃO\n")
    f.write("=" * 60 + "\n")
    f.write("Usar os valores da coluna 'suavizado' como ponto de partida.\n")
    f.write("Os valores 'raw' servem de referência para avaliar o impacto\n")
    f.write("do ruído de sensor na sintonização.\n")
    f.write("Ziegler-Nichols fornece um ponto de partida — ajuste fino\n")
    f.write("pode ser necessário após teste no processo real.\n")
    f.write("Referência: Ogata p.522 — 'as regras de sintonia de\n")
    f.write("Ziegler-Nichols fornecem estimativas dos valores dos\n")
    f.write("parâmetros e proporcionam um ponto de partida na sintonia\n")
    f.write("fina, e não os valores definitivos'.\n")

print("\nResultados guardados em zn_gains.txt")

# --- Visualização ---
t_tan = np.linspace(
    min(t_L_s, t_L_r) - 1.0,
    max(t_T_s, t_T_r) + 1.0,
    500
)
y_tan_s = y_inf_smooth + slope_smooth * (t_tan - t_inf_smooth)
y_tan_r = y_inf_raw    + slope_raw    * (t_tan - t_inf_raw)

fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 8))

for ax, t_inf, y_inf, slope, t_L, t_T, L, T, y_tan, Kp, Ki, Kd, label, cor in [
    (ax1, t_inf_smooth, y_inf_smooth, slope_smooth,
     t_L_s, t_T_s, L_s, T_s, y_tan_s, Kp_s, Ki_s, Kd_s, 'dy_smooth', 'r'),
    (ax2, t_inf_raw, y_inf_raw, slope_raw,
     t_L_r, t_T_r, L_r, T_r, y_tan_r, Kp_r, Ki_r, Kd_r, 'dy (raw)', 'orange'),
]:
    ax.plot(t, y, 'b', linewidth=0.8, label='y(t)')
    ax.plot(t_tan, y_tan, color=cor, linewidth=1.2, linestyle='--',
            label=f'Tangente ({label})')
    ax.axhline(y_repouso, color='gray',  linestyle=':',
               label=f'y_repouso = {y_repouso:.4f}')
    ax.axhline(y_final,   color='green', linestyle=':',
               label=f'y_final = {y_final:.4f}')
    ax.axvline(t_L, color='orange', linestyle='--', label=f'L = {L:.3f}s')
    ax.axvline(t_T, color='green',  linestyle='--',
               label=f'L+T = {t_T:.3f}s  (T={T:.3f}s)')
    ax.scatter([t_L, t_T], [y_repouso, y_final], zorder=5, color=cor, s=50)
    ax.scatter([t_inf], [y_inf], zorder=5, color='black', s=50, marker='x',
               label=f'inflexão t={t_inf:.3f}s')
    ax.set_title(f'{label}  →  Kp={Kp:.4f}  Ki={Ki:.4f}  Kd={Kd:.4f}')
    ax.set_ylabel('y (normalizado)')
    ax.legend(fontsize=8)
    ax.grid(True)

ax2.set_xlabel('Tempo [s]')
plt.tight_layout()
plt.savefig("zn.png", dpi=150)
print("Gráfico guardado em zn.png")