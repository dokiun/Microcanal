#!/usr/bin/env python3
"""Muestra los resultados de un caso en un instante indicado en milisegundos."""

import argparse

import numpy as np

from plot_results import PROJECT, load_case_data


def main():
    parser = argparse.ArgumentParser(
        description="Muestra las propiedades de postProcessing en un tiempo dado."
    )
    parser.add_argument("carpeta", help="Carpeta del caso dentro del proyecto")
    parser.add_argument("tiempo_ms", type=float, help="Tiempo solicitado en milisegundos")
    args = parser.parse_args()

    root = PROJECT / args.carpeta
    if root.resolve().parent != PROJECT or not root.is_dir():
        parser.error(f"Indica una carpeta existente dentro de {PROJECT}")

    data = load_case_data(root)
    times = data["time_ms"]
    t = args.tiempo_ms
    if not np.isfinite(t) or t < times[0] or t > times[-1]:
        parser.error(f"El tiempo debe estar entre {times[0]:.6g} y {times[-1]:.6g} ms")

    def value(key):
        return float(np.interp(t, times, data[key]))

    exact = np.any(np.isclose(times, t, rtol=0, atol=1e-9))
    print(f"Caso: {data['name']}")
    print(f"Tiempo: {t:.6g} ms ({'registro' if exact else 'interpolado'})")
    print(f"Caudal másico: {data['mdot']:.6g} kg/s")
    print(f"Flujo de calor en la base: {data['heat_flux']:.6g} W/m²")
    print(f"Caída de presión: {value('delta_p_pa'):.6g} Pa")
    print(f"Temperatura de la base: {value('t_base_k') - 273.15:.6g} °C")
    print(f"Temperatura de la pared: {value('t_wall_k') - 273.15:.6g} °C")
    print(f"Temperatura media del fluido: {value('t_fluid_k') - 273.15:.6g} °C")
    print(f"Coeficiente convectivo h: {value('h'):.6g} W/(m² K)")
    print(f"Número de Nusselt Nu: {value('nu'):.6g}")


if __name__ == "__main__":
    main()
