import time
import numpy as np

T = 0.1
t_degrau = 3.0
n = int(t_degrau / T)
niveis = [0.0, 0.5, 1.0, 0.0]

u_list = []
y_list = []

start_control()

for nivel in niveis:
    apply_input(nivel)
    print(f"Degrau aplicado: u = {nivel:.3f}")
    for i in range(n):
        y_val = read_output()
        u_list.append(nivel)
        y_list.append(y_val)
        print(f"  k={len(u_list):3d}  u={nivel:.3f}  y={y_val:.4f}")
        time.sleep(T)

stop_control()

u = np.array(u_list)
y = np.array(y_list)
print("Concluído.")
print("u:", np.round(u, 3))
print("y:", np.round(y, 3))