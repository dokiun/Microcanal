# Simulación térmica de un microcanal

Este proyecto estudia la transferencia de calor conjugada entre un microcanal de silicio y agua líquida, usando OpenFOAM y `chtMultiRegionTwoPhaseEulerFoam`. Se comparan tres condiciones de operación con el mismo dominio y diferentes números de Reynolds de entrada. El transporte multifásico sigue las fases líquida y gaseosa; el cambio de fase está desactivado actualmente.

## Casos disponibles

| Caso | Reynolds nominal | Velocidad inicial | Caudal másico |
|---|---:|---:|---:|
| `MicrocanalRe100V1` | 100 | 0.426 m/s | `2.57 × 10⁻⁵ kg/s` |
| `MicrocanalRe400V1` | 400 | 1.7090763 m/s | `1.0236 × 10⁻⁴ kg/s` |
| `MicrocanalRe800V1` | 800 | 3.4181527 m/s | `2.0472 × 10⁻⁴ kg/s` |

Los valores se definen en `0/fluid/U.liquid`. El campo local `ReDh` se calcula durante la simulación mediante `ReynoldsLocal` en `system/controlDict`.

## Geometría y modelo físico

El dominio representa una sección de silicio con dos medios canales simétricos. Sus dimensiones exteriores son **0.30 × 0.40 × 5 mm** y el diámetro hidráulico es **200 µm**.

![Geometría tridimensional del microcanal](MicrocanalRe100V1/imgs/Microcanal.png)

![Vista longitudinal del microcanal](MicrocanalRe100V1/imgs/Longitudinal.png)

Cada caso contiene dos regiones: `fluid` (agua líquida y fase gaseosa) y `solid` (silicio calentado). La geometría cerrada está en `geometry/Microcanal.stl`; la malla se genera con `AllmeshSTL` y la simulación se ejecuta con `Allrun`.

| Parámetro | Valor común |
|---|---:|
| Temperatura de entrada | 300 K |
| Calentamiento de la base | `10⁶ W/m²` |
| Presión de salida | `101325 Pa` |
| Longitud | 5 mm |
| Diámetro hidráulico | 200 µm |

La velocidad se estima con `Re_Dh = ρ U Dh / μ`.

## Estructura

```text
Microcanal/
├── MicrocanalRe100V1/    # Re ≈ 100
├── MicrocanalRe400V1/    # Re ≈ 400
├── MicrocanalRe800V1/    # Re ≈ 800
├── .gitignore
└── README.md
```

Dentro de cada caso: `0/` contiene las condiciones iniciales, `constant/` las propiedades y la malla, `system/` el control numérico, `geometry/` las superficies STL, `AllmeshSTL` genera la malla, `Allrun` ejecuta localmente y `run_hpc.slurm` envía el caso al clúster.

## Ejecución local

```bash
cd MicrocanalRe100V1       # cambiar por Re400V1 o Re800V1
source /ruta/a/OpenFOAM/etc/bashrc
bash AllmeshSTL
bash Allrun
```

Para revisar la malla:

```bash
checkMesh -constant -region fluid
checkMesh -constant -region solid
```

Para paralelizar manualmente:

```bash
decomposePar -allRegions -force
mpirun -np 4 chtMultiRegionTwoPhaseEulerFoam -parallel
reconstructPar -allRegions
```

## Ejecución en el clúster

```bash
sbatch MicrocanalRe100V1/run_hpc.slurm
sbatch MicrocanalRe400V1/run_hpc.slurm
sbatch MicrocanalRe800V1/run_hpc.slurm
```

Cada script solicita un nodo, cuatro tareas, 32 GB de memoria y hasta 48 horas. Verifica que el `cd` del script coincida con el nombre real de la carpeta.

## Resultados

Se comparan la caída de presión, temperaturas de base/pared/fluido, velocidad, presión, fracción de vapor, `ReDh`, convergencia y calidad de malla. Los resultados se guardan en `postProcessing/`, los logs en `logs/` y la paralelización en `processor*/`; estos artefactos están excluidos por el `.gitignore` común.

Para ejecutar las verificaciones:

```bash
python3 MicrocanalRe100V1/scripts/check_euler.py
python3 MicrocanalRe400V1/scripts/check_euler.py
python3 MicrocanalRe800V1/scripts/check_euler.py
```

Después de reconstruir los resultados, abre el archivo `.foam` correspondiente en ParaView.

Para consultar los valores calculados por `dataReduction` en un instante (en milisegundos):

```bash
python3 propiedades_en_tiempo.py MicrocanalRe100V1 1
```

El comando muestra los promedios de entrada, salida, interfaces, volumen y base, además de los mínimos y máximos de fase. Interpola entre registros cuando el tiempo solicitado no coincide con uno guardado.

> Nota: las tres carpetas son repositorios Git anidados. Los cambios de cada caso se confirman desde su propia carpeta.
