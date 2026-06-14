import time
import numpy as np

# --- Parâmetros ---
Kp = 4.424749
Ki = 7.195850
Kd = 0.680198

Ts       = 0.1
duration = 30.0   # duração de cada nível [s]

# Sequência de referências — (setpoint, duração em segundos)
levels_sp = [
    (0.2,  duration),
    (0.25, duration),
    (0.1,  duration),
    (0.2,  duration),
    (0.15, duration),
]

# --- Estado do controlador ---
# Referência: Paulo Gil p.7 — equação às diferenças
#   u(k) = u(k-1) + Kp*(e(k)-e(k-1)) + Ki*Ts*((e(k)+e(k-1))/2) + Kd/Ts*(e(k)-2*e(k-1)+e(k-2))
e_prev1 = 0.0   # e(k-1)
e_prev2 = 0.0   # e(k-2)
u_prev  = 0.0   # u(k-1)

# --- Listas de registo ---
u_list, y_list, sp_list = [], [], []

start_control()
t0     = time.monotonic()
offset = 0

for setpoint, dur in levels_sp:
    n = int(dur / Ts)
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
        sp_list.append(setpoint)

        e_prev2 = e_prev1
        e_prev1 = e
        u_prev  = u

        time.sleep(max(0, t0 + (offset + k + 1) * Ts - time.monotonic()))

    offset += n

stop_control()

u  = np.array(u_list)
y  = np.array(y_list)
sp = np.array(sp_list)
t  = np.arange(len(u_list)) * Ts

# ISE total
squared_error_sum_total = np.sum((sp - y)**2) * Ts

print(f"Concluído. {len(t)} amostras, duração {t[-1]:.1f}s")
print(f"squared error sum total (ISE): {squared_error_sum_total:.6f}")
print()

for i, (setpoint, dur) in enumerate(levels_sp):
    n                       = int(dur / Ts)
    inicio                  = sum(int(d / Ts) for _, d in levels_sp[:i])
    fim                     = inicio + n
    y_seg                   = y[inicio:fim]
    sp_seg                  = sp[inicio:fim]
    squared_error_sum_seg   = np.sum((sp_seg - y_seg)**2) * Ts
    print(f"  setpoint={setpoint:.2f} → "
          f"y final (média últimas 10): {y_seg[-10:].mean():.4f}  "
          f"erro: {abs(setpoint - y_seg[-10:].mean()):.4f}  "
          f"squared error sum (ISE): {squared_error_sum_seg:.6f}")