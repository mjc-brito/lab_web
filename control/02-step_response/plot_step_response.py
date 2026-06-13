import numpy as np
import matplotlib.pyplot as plt

data = np.load("uyt.npz")
u = data["u"]
y = data["y"]
t = data["t"]

u_v = 0.60 + u * 2.45
y_v = y * 9.9

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(t, u_v, "b-", linewidth=1.5, label="u (atuação)")
ax.plot(t, y_v, "r-", linewidth=1.5, label="y (leitura)")
ax.set_xlabel("Tempo (s)")
ax.set_ylabel("Tensão (V)")
ax.set_title("Resposta ao degrau — PCT 37-100")
ax.legend()
ax.grid(True)
ax.set_xlim(0, 30)
ax.set_ylim(-0.05, 4)
plt.tight_layout()
plt.savefig("step_response.png", dpi=150)