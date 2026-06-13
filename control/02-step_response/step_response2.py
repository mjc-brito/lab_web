import time
import numpy as np

Ts     = 0.1
levels = [(0.0, 5.0), (1.0, 120.0), (0.0, 30.0)]

u_list, y_list = [], []

start_control()

t0     = time.monotonic()
offset = 0
for level, duration in levels:
    apply_input(level)
    n = int(duration / Ts)
    for k in range(n):
        y_list.append(read_output())
        u_list.append(level)
        time.sleep(max(0, t0 + (offset + k + 1) * Ts - time.monotonic()))
    offset += n

stop_control()

u = np.array(u_list)
y = np.array(y_list)
t = np.arange(len(u_list)) * Ts