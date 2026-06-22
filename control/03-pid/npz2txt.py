import numpy as np

ficheiros = [
    "../02-step_response/uyt2.npz",
    "variaveis_pid_raw.npz",
    "variaveis_pid_smooth.npz",
]

for caminho in ficheiros:
    nome_txt = caminho.split("/")[-1].replace(".npz", ".txt")

    try:
        data = np.load(caminho)
    except FileNotFoundError:
        print(f"Ficheiro não encontrado: {caminho}")
        continue

    with open(nome_txt, "w") as f:
        f.write(f"Ficheiro de origem: {caminho}\n")
        f.write(f"Variáveis: {data.files}\n\n")

        for key in data.files:
            arr = data[key]
            f.write(f"=== {key} ===\n")
            f.write(f"shape={arr.shape}  dtype={arr.dtype}\n")
            f.write(f"min={arr.min():.8f}  max={arr.max():.8f}  mean={arr.mean():.8f}\n")
            f.write("valores:\n")
            np.savetxt(f, arr.reshape(-1, 1), fmt="%.8f")
            f.write("\n")

    print(f"Guardado: {nome_txt}")