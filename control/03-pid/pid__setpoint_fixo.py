import time
import numpy as np

# --- Parâmetros ---
Kp = 4.424749
Ki = 7.195850
Kd = 0.680198

Ts       = 0.1
setpoint = 0.2
duration = 120.0

# --- Estado do controlador ---
# Referência: Paulo Gil p.7 — equação às diferenças
#   u(k) = u(k-1) + Kp*(e(k)-e(k-1)) + Ki*Ts*((e(k)+e(k-1))/2) + Kd/Ts*(e(k)-2*e(k-1)+e(k-2))
e_prev1 = 0.0   # e(k-1)
e_prev2 = 0.0   # e(k-2)
u_prev  = 0.0   # u(k-1)

# --- Listas de registo ---
u_list, y_list = [], []

start_control()
t0     = time.monotonic()
n      = int(duration / Ts)
offset = 0

for k in range(n):
    y = read_output()
    e = setpoint - y

    # Equação às diferenças — Paulo Gil p.7
    u = (u_prev
         + Kp * (e - e_prev1)
         + Ki * Ts * (e + e_prev1) / 2.0
         + Kd / Ts * (e - 2.0 * e_prev1 + e_prev2))

    u = float(np.clip(u, 0.0, 1.0))
    apply_input(u)

    u_list.append(u)
    y_list.append(y)

    e_prev2 = e_prev1
    e_prev1 = e
    u_prev  = u

    time.sleep(max(0, t0 + (offset + k + 1) * Ts - time.monotonic()))

stop_control()

u = np.array(u_list)
y = np.array(y_list)
t = np.arange(len(u_list)) * Ts

# Erro calculado offline sobre os arrays finais
e                  = setpoint - y
squared_error_sum  = np.sum(e**2) * Ts

print(f"Concluído. {len(t)} amostras, duração {t[-1]:.1f}s")
print(f"setpoint: {setpoint:.4f}")
print(f"y final (média últimas 50): {y[-50:].mean():.4f}")
print(f"erro final: {abs(setpoint - y[-50:].mean()):.4f}")
print(f"squared error sum (ISE): {squared_error_sum:.6f}")