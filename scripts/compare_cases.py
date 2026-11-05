#!/usr/bin/env python3
"""Compara series temporales de varios casos OpenFOAM en PNG separados."""

from pathlib import Path
import argparse
import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
import matplotlib.pyplot as plt

if __package__:
    from .plot_results import PROJECT, load_case_data
else:
    from plot_results import PROJECT, load_case_data


PLOTS = PROJECT / "plots"
THERMAL_START_MS = 10.0  # Excluye el pico artificial cuando Tpared ≈ Tfluido.
PRESSURE_START_MS = 0.1
PRESSURE_END_MS = 1.0  # La caída de presión se estabiliza mucho antes que h.
METRICS = (
    ("temperatura_base", "t_base_k", "Temperatura de la base", "Temperatura [°C]", lambda values: values - 273.15),
    ("temperatura_pared", "t_wall_k", "Temperatura de la pared", "Temperatura [°C]", lambda values: values - 273.15),
    ("temperatura_fluido", "t_fluid_k", "Temperatura media del fluido", "Temperatura [°C]", lambda values: values - 273.15),
    ("caida_presion", "delta_p_pa", "Caída de presión", "Δp [kPa]", lambda values: values / 1000),
    ("coeficiente_convectivo", "h", "Coeficiente convectivo", "h [W/(m² K)]", lambda values: values),
    ("nusselt", "nu", "Número de Nusselt", "Nu [–]", lambda values: values),
)


def case_folder(name):
    folder = PROJECT / name
    if not name or folder.resolve().parent != PROJECT or not folder.is_dir():
        raise ValueError(f"La carpeta {name!r} no existe dentro de {PROJECT}")
    return folder


def select_cases(args=None):
    parser = argparse.ArgumentParser(description="Compara dos o más carpetas de casos")
    parser.add_argument("carpetas", nargs="*", help="Nombres de carpetas dentro del proyecto")
    names = parser.parse_args(args).carpetas
    if names:
        if len(names) < 2:
            parser.error("Indica al menos dos carpetas")
        try:
            folders = [case_folder(name) for name in names]
        except ValueError as error:
            parser.error(str(error))
        if len(set(folders)) != len(folders):
            parser.error("Cada carpeta debe aparecer una sola vez")
        return folders

    while True:
        raw = input("¿Cuántos casos deseas comparar? (mínimo 2): ").strip()
        if raw.isdigit() and int(raw) >= 2:
            count = int(raw)
            break
        print("Introduce un número entero mayor o igual a 2.")

    folders = []
    for index in range(1, count + 1):
        while True:
            name = input(f"Nombre de la carpeta del caso {index}: ").strip()
            try:
                folder = case_folder(name)
            except ValueError as error:
                print(error)
                continue
            if folder in folders:
                print("Ese caso ya fue seleccionado.")
                continue
            folders.append(folder)
            break
    return folders


def main():
    folders = select_cases()
    data = []
    for folder in folders:
        try:
            data.append(load_case_data(folder))
        except (FileNotFoundError, ValueError) as error:
            raise SystemExit(f"No se pudieron cargar los datos de {folder.name}: {error}") from error

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    colors = plt.get_cmap("tab20" if len(data) <= 20 else "hsv").resampled(len(data))
    PLOTS.mkdir(exist_ok=True)
    for filename, key, title, ylabel, convert in METRICS:
        fig, ax = plt.subplots(figsize=(10, 6), dpi=200)
        for index, case in enumerate(data):
            times = case["time_ms"]
            values = convert(case[key])
            if key == "delta_p_pa":
                mask = (times >= PRESSURE_START_MS) & (times <= PRESSURE_END_MS)
                if not mask.any():
                    raise SystemExit(f"{case['name']} no tiene datos de presión entre "
                                     f"{PRESSURE_START_MS:g} y {PRESSURE_END_MS:g} ms")
                times, values = times[mask], values[mask]
            elif key in ("h", "nu"):
                mask = times >= THERMAL_START_MS
                if not mask.any():
                    raise SystemExit(f"{case['name']} no tiene datos de {key} desde {THERMAL_START_MS:g} ms")
                times, values = times[mask], values[mask]
            ax.plot(times, values, label=case["name"], color=colors(index), linewidth=1.8)
        if key == "delta_p_pa":
            ax.set_title(f"{title} ({PRESSURE_START_MS:g}–{PRESSURE_END_MS:g} ms)")
        elif key in ("h", "nu"):
            ax.set_title(f"{title} (desde {THERMAL_START_MS:g} ms)")
        else:
            ax.set_title(title)
        ax.set_xlabel("Tiempo [ms]")
        ax.set_ylabel(ylabel)
        ax.legend(title="Caso", loc="best")
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.tight_layout()
        output = PLOTS / f"comparacion_{filename}.png"
        fig.savefig(output, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Gráfica: {output}")


if __name__ == "__main__":
    main()
