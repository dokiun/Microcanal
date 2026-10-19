#!/usr/bin/env python3
"""Calculadora de velocidad y caudal másico para un fluido.

Unidades predeterminadas:
  - viscosidad dinámica: mPa·s
  - diámetro hidráulico: µm
  - área transversal: µm²
  - densidad: kg/m³
Salidas: velocidad en m/s y caudal másico en kg/s.
"""
from __future__ import annotations
import math


UNIDADES_VISCOSIDAD = {
    "1": ("mPa·s", 1e-3),
    "2": ("Pa·s", 1.0),
    "3": ("cP", 1e-3),
}
UNIDADES_LONGITUD = {
    "1": ("µm", 1e-6),
    "2": ("mm", 1e-3),
    "3": ("cm", 1e-2),
    "4": ("m", 1.0),
}
UNIDADES_AREA = {
    "1": ("µm²", 1e-12),
    "2": ("mm²", 1e-6),
    "3": ("cm²", 1e-4),
    "4": ("m²", 1.0),
}


def pedir_numero(mensaje: str, predeterminado: float | None = None, *, positivo: bool = True) -> float:
    while True:
        sufijo = f" [{predeterminado}]" if predeterminado is not None else ""
        entrada = input(f"{mensaje}{sufijo}: ").strip().replace(",", ".")
        if not entrada and predeterminado is not None:
            valor = predeterminado
        else:
            try:
                valor = float(entrada)
            except ValueError:
                print("  Introduce un número válido.")
                continue
        if not math.isfinite(valor) or (positivo and valor <= 0):
            print("  Introduce un número finito mayor que cero.")
            continue
        return valor


def elegir_unidad(etiqueta: str, unidades: dict[str, tuple[str, float]]) -> tuple[str, float]:
    print(f"\nUnidad de {etiqueta} (Enter = opción 1):")
    for clave, (nombre, _) in unidades.items():
        print(f"  {clave}. {nombre}")
    while True:
        eleccion = input("Selecciona una opción [1]: ").strip() or "1"
        if eleccion in unidades:
            return unidades[eleccion]
        print("  Opción no válida.")


def main() -> None:
    print("=" * 56)
    print("    VELOCIDAD POR REYNOLDS Y CAUDAL MÁSICO")
    print("=" * 56)
    print("Pulsa Enter para aceptar los valores/unidades por defecto.")

    print("\n1) VELOCIDAD DEL FLUIDO")
    reynolds = pedir_numero("Número de Reynolds (adimensional)")
    nombre_d, factor_d = elegir_unidad("diámetro hidráulico", UNIDADES_LONGITUD)
    diametro = pedir_numero(f"Diámetro hidráulico ({nombre_d})") * factor_d

    nombre_mu, factor_mu = elegir_unidad("viscosidad dinámica", UNIDADES_VISCOSIDAD)
    viscosidad = pedir_numero(f"Viscosidad dinámica ({nombre_mu})", 1.002) * factor_mu
    densidad = pedir_numero("Densidad del agua (kg/m³)", 998.2)

    velocidad = reynolds * viscosidad / (densidad * diametro)
    if not math.isfinite(velocidad):
        print("Los parámetros producen un resultado fuera del rango numérico.")
        return
    print(f"\n  Velocidad: {velocidad:.8g} m/s")

    print("\n2) CAUDAL MÁSICO")
    nombre_a, factor_a = elegir_unidad("área transversal", UNIDADES_AREA)
    area = pedir_numero(f"Área transversal ({nombre_a})") * factor_a
    caudal_masico = densidad * velocidad * area
    caudal_volumetrico = velocidad * area
    if not all(math.isfinite(x) for x in (caudal_masico, caudal_volumetrico)):
        print("Los parámetros producen un resultado fuera del rango numérico.")
        return

    print("\n" + "=" * 56)
    print("RESULTADOS")
    print(f"  Velocidad:          {velocidad:.8g} m/s")
    print(f"  Caudal másico:      {caudal_masico:.8g} kg/s")
    print(f"  Caudal volumétrico: {caudal_volumetrico:.8g} m³/s")
    print("=" * 56)
    print("Fórmulas: v = Re·µ/(ρ·Dh)    ṁ = ρ·v·A")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nOperación cancelada.")
