import numpy as np
import matplotlib.pyplot as plt

data = np.load("../02-step_response/uyt2.npz")
t_full = data["t"]
u_full = data["u"]
y_full = data["y"]

# -----------------------------------------------------------------------
# RECORTE DO SINAL
#
# O ensaio tem três fases: repouso inicial (u=0), degrau activo, repouso
# final (u=0). Precisamos apenas da fase do degrau.
#
# Estratégia: encontrar o primeiro índice onde u sobe acima de um limiar
# (início do degrau) e o primeiro índice onde u cai de volta a zero
# (fim do degrau). O recorte é feito com uma pequena margem antes e
# depois para ver o regime estacionário de ambos os lados.
# -----------------------------------------------------------------------

THRESHOLD = 0.05   # limiar para considerar que o degrau está activo

# Máscara booleana onde o degrau está activo
degrau_activo = u_full > THRESHOLD

# Índice do primeiro sample com degrau activo
idx_inicio = np.argmax(degrau_activo)

# Índice do último sample com degrau activo
# (argmax na versão invertida + ajuste)
idx_fim = len(degrau_activo) - 1 - np.argmax(degrau_activo[::-1])

# Verificação básica
print(f"Degrau activo de t={t_full[idx_inicio]:.2f}s até t={t_full[idx_fim]:.2f}s")
print(f"Duração do degrau: {t_full[idx_fim] - t_full[idx_inicio]:.2f}s")
print(f"Total de amostras no degrau: {idx_fim - idx_inicio + 1}")

# Recorte: fica apenas a janela do degrau
t = t_full[idx_inicio : idx_fim + 1]
u = u_full[idx_inicio : idx_fim + 1]
y = y_full[idx_inicio : idx_fim + 1]

# Reonzar t para começar em 0
t = t - t[0]

# -----------------------------------------------------------------------
# AMPLITUDE DO DEGRAU E GANHO ESTÁTICO K
#
# u_step: média de u durante o degrau (robusto a ruído)
# y_inicial: média das primeiras amostras de y (antes da saída reagir)
# y_final: média das últimas amostras de y (regime estacionário)
#
# Usamos médias de uma janela e não y[0] / y[-1] individuais porque
# pode haver ruído de medição nos extremos.
# -----------------------------------------------------------------------

N_janela = max(5, len(t) // 20)   # janela de ~5% do sinal ou mínimo 5 amostras

u_step   = u.mean()               # u é constante durante o degrau (valor normalizado)
y_inicial = y[:N_janela].mean()   # valor médio antes de a saída reagir
y_final   = y[-N_janela:].mean()  # valor médio em regime estacionário

# Ganho estático (adimensional, tudo em [0,1])
# Referência: Ogata Cap.8 p.523 — C(s)/U(s) = K·e^(-Ls)/(Ts+1)
# K = variação de saída em regime / variação de entrada
K = (y_final - y_inicial) / u_step

print(f"\nu_step   = {u_step:.4f}  (normalizado, ~3.05V no actuador)")
print(f"y_inicial = {y_inicial:.4f}")
print(f"y_final   = {y_final:.4f}")
print(f"K         = {K:.4f}  (ganho estático adimensional)")

# -----------------------------------------------------------------------
# PONTO DE INFLEXÃO E TANGENTE
#
# A derivada dy/dt é máxima no ponto de inflexão da curva em S.
# Referência: Paulo Gil p.5 — "traçar a tangente ao ponto de inflexão"
#             Ogata p.523, Figura 8.3
# -----------------------------------------------------------------------

dy = np.gradient(y, t)

# Para robustez, suavizar a derivada antes de encontrar o máximo
# (ruído de medição pode criar picos espúrios na derivada)
from numpy.lib.stride_tricks import sliding_window_view
N_smooth = max(3, N_janela // 2)
# Convolução com janela rectangular para suavização
kernel = np.ones(N_smooth) / N_smooth
dy_smooth = np.convolve(dy, kernel, mode='same')

idx_inf = np.argmax(dy_smooth)
t_inf   = t[idx_inf]
y_inf   = y[idx_inf]
slope   = dy_smooth[idx_inf]      # declive da tangente no ponto de inflexão

print(f"\nPonto de inflexão: t={t_inf:.4f}s, y={y_inf:.4f}, slope={slope:.6f}/s")

# -----------------------------------------------------------------------
# CÁLCULO DE L E T
#
# Equação da tangente: y_tan(t) = y_inf + slope*(t - t_inf)
#
# L: onde a tangente cruza y_inicial (nível antes do degrau)
#    y_inicial = y_inf + slope*(t_L - t_inf)  =>  t_L = t_inf - (y_inf - y_inicial)/slope
#    L = t_L - 0  (t já começa em 0)
#
# T: onde a tangente cruza y_final (nível estacionário)
#    y_final = y_inf + slope*(t_T - t_inf)  =>  t_T = t_inf + (y_final - y_inf)/slope
#    T = t_T - t_L  (largura entre as duas intersecções)
#
# Referência: Paulo Gil p.5, gráfico central — setas L e T no eixo do tempo
#             Ogata p.523, Figura 8.3 e texto: "intersecção da tangente com
#             o eixo dos tempos e a linha c(t) = K"
# -----------------------------------------------------------------------

t_L = t_inf - (y_inf - y_inicial) / slope   # instante onde tangente cruza y_inicial
t_T = t_inf + (y_final - y_inf)  / slope    # instante onde tangente cruza y_final

L = t_L          # atraso (assumindo que t começa em 0 e y_inicial é o nível de repouso)
T = t_T - t_L    # constante de tempo

print(f"\nL = {L:.4f} s  (atraso)")
print(f"T = {T:.4f} s  (constante de tempo)")

# -----------------------------------------------------------------------
# VISUALIZAÇÃO — para confirmar que L e T fazem sentido graficamente
# -----------------------------------------------------------------------

t_plot = np.linspace(t_L - 0.5*L, t_T + 0.2*T, 300)
y_tan  = y_inf + slope * (t_plot - t_inf)

fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

# Gráfico da saída
axes[0].plot(t, y, 'b-', linewidth=1.5, label='y(t) — saída medida')
axes[0].plot(t_plot, y_tan, 'r--', linewidth=1.2, label='Tangente no ponto de inflexão')
axes[0].axhline(y_inicial, color='gray', linestyle=':', label=f'y inicial = {y_inicial:.3f}')
axes[0].axhline(y_final,   color='gray', linestyle='-.', label=f'y final = {y_final:.3f}')
axes[0].axvline(t_L, color='orange', linestyle='--', label=f'L = {L:.3f}s')
axes[0].axvline(t_T, color='green',  linestyle='--', label=f'L+T = {t_T:.3f}s')
axes[0].set_ylabel('y (normalizado)')
axes[0].set_title('Método da curva de reacção — Paulo Gil p.5 / Ogata p.523')
axes[0].legend(fontsize=8)
axes[0].grid(True)

# Gráfico da entrada
axes[1].plot(t, u, 'k-', linewidth=1.5, label='u(t) — entrada (normalizado)')
axes[1].set_ylabel('u (normalizado)')
axes[1].set_xlabel('Tempo [s]')
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
plt.savefig("curva_reaccao.png", dpi=150)
plt.show()
print("\nGráfico guardado em curva_reaccao.png")