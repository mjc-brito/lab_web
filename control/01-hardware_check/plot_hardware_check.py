import numpy as np
import matplotlib.pyplot as plt

data = np.load("uyt.npz")
u = data["u"]
y = data["y"]
t = data["t"]

u = (0.60 + u * 2.45)
y = y * 9.9

fig, ax = plt.subplots(figsize=(12, 5))

ax.plot(t, u, "b-", linewidth=1.5, label="u (atuação)")
ax.plot(t, y, "r-", linewidth=1.5, label="y (leitura)")

ax.set_xlabel("Tempo (s)")
ax.set_ylabel("Tensão (V)")
ax.set_title("Teste de hardware — o sinal de atuação é injetado diretamente na entrada")
ax.legend()
ax.grid(True)
ax.set_ylim(-0.05, 4)

plt.tight_layout()
plt.savefig("img_hardware_check.png", dpi=150)