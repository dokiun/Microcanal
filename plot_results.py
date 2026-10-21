#!/usr/bin/env python3
"""Grafica presión y transferencia térmica a partir de postProcessing.

Los parámetros de cada caso se leen de sus condiciones de contorno y de los
encabezados de OpenFOAM; no se comparten caudales entre casos Re distintos.
"""
from pathlib import Path
import argparse
import os
import re

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
import matplotlib.pyplot as plt

PROJECT = Path(__file__).resolve().parent
DH = 200e-6  # m; sección nominal de canal 0.15 x 0.30 mm


def foam_value(path, pattern, label):
    content = re.sub(r"//[^\n]*", "", path.read_text())
    match = re.search(pattern, content, re.S)
    if not match:
        raise ValueError(f"No se encontró {label} en {path}")
    return float(match.group(1))


def case_parameters(root):
    mdot = foam_value(root / "0/fluid/U.liquid", r"massFlowRate\s+constant\s+([\d.eE+-]+)\s*;", "massFlowRate")
    liquid = root / "constant/fluid/thermophysicalProperties.liquid"
    conductivity = re.search(r"\bkappa\s*\((.*?)\)\s*;", re.sub(r"//[^\n]*", "", liquid.read_text()), re.S)
    if not conductivity:
        raise ValueError(f"No se encontró la tabla kappa en {liquid}")
    pairs = np.array([(float(t), float(k)) for t, k in re.findall(r"\(\s*([\d.eE+-]+)\s+([\d.eE+-]+)\s*\)", conductivity.group(1))])
    if len(pairs) < 2:
        raise ValueError(f"Tabla kappa inválida en {liquid}")
    gradient = foam_value(root / "0/solid/T", r"outerBottom\s*\{.*?gradient\s+uniform\s+([\d.eE+-]+)\s*;", "gradient de outerBottom")
    solid_k = foam_value(root / "constant/solid/thermophysicalProperties", r"\bkappa\s+([\d.eE+-]+)\s*;", "kappa del sólido")
    return mdot, pairs, abs(gradient * solid_k)


def read_series(root, region, name):
    folder = root / "postProcessing" / region / name
    files = sorted(folder.glob("*/*.dat"))
    rows = {}
    area = None
    for path in files:
        for line in path.read_text().splitlines():
            if line.startswith("# Area"):
                area = float(line.split(":", 1)[1])
            elif line and not line.startswith("#"):
                values = [float(x) for x in line.replace("(", " ").replace(")", " ").split()]
                rows[values[0]] = values[1:]
    if not rows:
        raise FileNotFoundError(f"Sin datos para {region}/{name} en {folder}")
    times = np.array(sorted(rows))
    return times, np.array([rows[t] for t in times]), area


def on_times(series, times, column):
    source_t, values, _ = series
    if times[0] < source_t[0] or times[-1] > source_t[-1]:
        raise ValueError("Los registros de postProcessing no cubren los mismos tiempos")
    return np.interp(times, source_t, values[:, column])


def select_case():
    parser = argparse.ArgumentParser(description="Grafica resultados de una carpeta de caso")
    parser.add_argument("carpeta", nargs="?", help="Nombre de la carpeta del caso dentro del proyecto")
    args = parser.parse_args()
    if args.carpeta:
        folder = PROJECT / args.carpeta
        if folder.resolve().parent != PROJECT or not folder.is_dir():
            parser.error(f"Indica una carpeta existente dentro de {PROJECT}")
        return folder
    while True:
        name = input("Nombre de la carpeta del caso: ").strip()
        folder = PROJECT / name
        if name and folder.resolve().parent == PROJECT and folder.is_dir():
            return folder
        print(f"No existe esa carpeta dentro de {PROJECT}.")


def load_case_data(root):
    mdot, conductivity, heat_flux = case_parameters(root)
    inlet = read_series(root, "fluid", "inletFluid")
    outlet = read_series(root, "fluid", "outletFluid")
    base = read_series(root, "solid", "baseSolid")
    wall = read_series(root, "solid", "interfaceSolid")
    volume = read_series(root, "fluid", "volFluid")

    times = inlet[0]
    # El archivo volFieldValue.dat puede estar vacío y los datos en _0.dat.
    p_in = inlet[1][:, 0]
    p_out = on_times(outlet, times, 0)
    t_base = on_times(base, times, 0)
    t_wall = on_times(wall, times, 0)
    t_fluid = on_times(volume, times, 0)
    k_fluid = np.interp(t_fluid, conductivity[:, 0], conductivity[:, 1])
    delta_p = p_in - p_out
    area_conv = wall[2]
    if area_conv is None or base[2] is None or area_conv <= 0:
        raise ValueError("Faltan las áreas de base o interfaz en postProcessing")
    q_total = heat_flux * base[2]
    delta_t = t_wall - t_fluid
    # Un ΔT nulo o negativo no define un coeficiente convectivo útil.
    h = np.full_like(delta_t, np.nan)
    valid = delta_t > 0
    h[valid] = q_total / (area_conv * delta_t[valid])
    nu = h * DH / k_fluid

    return {
        "name": root.name,
        "time_ms": times * 1e3,
        "mdot": mdot,
        "heat_flux": heat_flux,
        "area_base": base[2],
        "area_conv": area_conv,
        "delta_p_pa": delta_p,
        "t_base_k": t_base,
        "t_wall_k": t_wall,
        "t_fluid_k": t_fluid,
        "h": h,
        "nu": nu,
        "invalid_h": np.count_nonzero(~valid),
    }


def main():
    root = select_case()
    plots = root / "plots"
    data = load_case_data(root)
    times = data["time_ms"]
    mdot = data["mdot"]
    heat_flux = data["heat_flux"]
    delta_p = data["delta_p_pa"]
    t_base = data["t_base_k"]
    t_wall = data["t_wall_k"]
    t_fluid = data["t_fluid_k"]
    h = data["h"]
    nu = data["nu"]

    print(f"Caso: {root.name}; caudal másico: {mdot:.6g} kg/s; flujo base: {heat_flux:.6g} W/m²")
    print(f"Áreas: base {data['area_base']:.6g} m²; interfaz {data['area_conv']:.6g} m²; Dh {DH:.6g} m")
    print(f"Último registro: t={times[-1] / 1000:.6g} s, Δp={delta_p[-1]:.3f} Pa, "
          f"Tbase={t_base[-1]:.3f} K, Tpared={t_wall[-1]:.3f} K, "
          f"Tfluido={t_fluid[-1]:.3f} K, h={h[-1]:.3f} W/(m² K), Nu={nu[-1]:.3f}")
    if data["invalid_h"]:
        print(f"Aviso: se omitieron {data['invalid_h']} puntos con Tpared ≤ Tfluido")

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), dpi=200)
    t_ms = times
    ax = axes[0, 0]
    ax.plot(t_ms, t_base - 273.15, label="Base", color="#dc2626")
    ax.plot(t_ms, t_wall - 273.15, label="Pared", color="#d97706")
    ax.plot(t_ms, t_fluid - 273.15, label="Fluido medio", color="#2563eb")
    ax.set_ylabel("Temperatura [°C]")
    ax.set_title("Temperaturas")
    ax.legend()

    ax = axes[0, 1]
    ax.plot(t_ms, delta_p / 1000, color="#059669")
    ax.set_ylabel("Caída de presión [kPa]")
    ax.set_title("Caída de presión")

    ax = axes[1, 0]
    ax.plot(t_ms, h, color="#ea580c")
    ax.set_ylabel("h [W/(m² K)]")
    ax.set_title("Coeficiente convectivo")

    ax = axes[1, 1]
    ax.plot(t_ms, nu, color="#2563eb")
    ax.set_ylabel("Nu [–]")
    ax.set_title("Número de Nusselt")

    for ax in axes.flat:
        ax.set_xlabel("Tiempo [ms]")
        ax.grid(True, linestyle="--", alpha=0.5)
    fig.suptitle(f"Microcanal {root.name} — ṁ = {mdot:.6g} kg/s")
    fig.tight_layout()
    plots.mkdir(exist_ok=True)
    output = plots / "resultados_ghani_mcrc.png"
    fig.savefig(output, dpi=300)
    print(f"Gráfica: {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
