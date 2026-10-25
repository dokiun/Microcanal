# Simulación térmica de microcanales

Este proyecto contiene seis casos OpenFOAM de transferencia de calor conjugada entre agua y silicio. Se usa `chtMultiRegionTwoPhaseEulerFoam` con las regiones `fluid` y `solid`, tres caudales de entrada y dos variantes por caudal. El sistema incluye las fases `liquid` y `gas`, pero `phaseChange` está **desactivado** en `constant/fluid/phaseProperties`.

## Casos

| Reynolds del nombre (nominal) | Variante V1 | Variante V2 | Caudal másico impuesto |
|---:|---|---|---:|
| 100 | [`MicrocanalRe100V1`](MicrocanalRe100V1/) | [`MicrocanalRe100V2`](MicrocanalRe100V2/) | 2,57 × 10⁻⁵ kg/s |
| 400 | [`MicrocanalRe400V1`](MicrocanalRe400V1/) | [`MicrocanalRe400V2`](MicrocanalRe400V2/) | 1,0236 × 10⁻⁴ kg/s |
| 800 | [`MicrocanalRe800V1`](MicrocanalRe800V1/) | [`MicrocanalRe800V2`](MicrocanalRe800V2/) | 2,0472 × 10⁻⁴ kg/s |

El caudal se lee de `0/fluid/U.liquid`. El número de Reynolds del nombre identifica la condición nominal; el Reynolds calculado a partir del caudal puede diferir. Las variantes V1 y V2 comparten geometría, malla y caudal. En `system/controlDict`, V1 calcula `ReDh` con `rho.liquid` al escribir resultados; V2 usa una densidad constante de 997 kg/m³ y lo calcula cada diez pasos. Cada carpeta tiene una ficha `<nombre-del-caso>.dat` con los parámetros de sus archivos y logs.

## Geometría y física

![Geometría tridimensional del microcanal](imgs/Microcanal.png)

![Vista longitudinal del microcanal](imgs/Longitudinal.png)

`geometry/Microcanal.stl` describe una pieza de silicio en I y dos medios canales laterales. La envolvente mide 0,30 × 0,40 × 5 mm. La simetría lateral representa un canal completo de 0,15 × 0,30 mm, con diámetro hidráulico de 200 µm. La malla final tiene 645.120 celdas fluidas y 409.600 sólidas según `logs/log.checkMesh.*`.

La entrada del líquido está a 300 K y la presión impuesta en la salida es 101.325 Pa. La base `outerBottom` aplica `fixedGradient` de 7.692,307692 K/m; con la conductividad del sólido de 130 W/(m·K), equivale a un flujo de 10⁶ W/m². Los scripts de ejecución cargan OpenFOAM v2506 y los logs de mallado registran esa versión; algunos encabezados heredados de los diccionarios muestran versiones distintas.

## Organización

```text
Microcanal/
├── MicrocanalRe100V1/  MicrocanalRe100V2/
├── MicrocanalRe400V1/  MicrocanalRe400V2/
├── MicrocanalRe800V1/  MicrocanalRe800V2/
├── imgs/                # imágenes usadas en este README
├── scripts/             # análisis y gráficos en Python
├── plots/               # comparaciones entre casos
├── .gitignore
└── README.md
```

En cada caso, `0/` contiene los campos iniciales y condiciones de contorno; `constant/`, las propiedades y mallas; `system/`, el control numérico; `geometry/`, el STL; y `logs/`, las comprobaciones y registros de ejecución. Las seis carpetas pertenecen al repositorio Git de esta raíz; no tienen repositorios internos.

## Ejecución

Carga OpenFOAM v2506 y ejecuta desde la raíz del proyecto:

```bash
cd MicrocanalRe100V1   # sustituir por cualquiera de los seis casos
source /ruta/a/OpenFOAM/etc/bashrc
bash Allrun             # comprueba las mallas existentes y ejecuta el solver
```

`bash AllmeshSTL` vuelve a generar la malla desde el STL; úsalo cuando necesites reconstruirla. Para comprobar la malla existente sin iniciar la simulación:

```bash
checkMesh -constant -region fluid
checkMesh -constant -region solid
```

## Análisis de resultados

Ejecuta estos comandos desde la raíz del proyecto. Requieren Python 3, NumPy y Matplotlib; los gráficos que leen la simulación requieren datos en `postProcessing/`.

```bash
python3 -m scripts.plot_results MicrocanalRe100V1
python3 -m scripts.propiedades_en_tiempo MicrocanalRe100V1 1  # tiempo en ms
python3 -m scripts.compare_cases MicrocanalRe100V1 MicrocanalRe400V1 MicrocanalRe800V1
python3 -m scripts.compare_friction MicrocanalRe100V1 MicrocanalRe400V1 MicrocanalRe800V1
python3 -m scripts.plot_nux MicrocanalRe100V1 MicrocanalRe400V1 MicrocanalRe800V1 --re nominal
```

`plot_results` guarda una gráfica en `plots/` dentro del caso. Las comparaciones guardan sus figuras en `plots/` de la raíz. `plot_nux` calcula la correlación longitudinal de Nusselt y exporta CSV; permite `--re calculado` para usar el Reynolds obtenido del caudal. Los gráficos temporales usan solo el intervalo cubierto por todas las series necesarias y no extrapolan registros faltantes.

Los archivos `.foam` de cada carpeta se pueden abrir en ParaView. `postProcessing/`, `processor*/`, logs y archivos `.foam` generados están excluidos por el `.gitignore` de la raíz.

# Cálculo de `NuLocal`

El número de Nusselt local se calcula a lo largo del canal, cuya dirección
principal es `z`, mediante:

```text
NuLocal(z) = q''w(z) * Dh / [kl(Tb(z)) * (Tw(z) - Tb(z))]
```

donde:

- `Dh = 0.0002 m` es el diámetro hidráulico.
- `q''w(z)` es el flujo de calor local en la interfaz `fluid_to_solid`.
- `Tw(z)` es la temperatura local de pared inferior obtenida en `fluid_to_solid`.
- `Tb(z)` se define aquí como la temperatura `T.liquid` sobre la línea central
  del fluido, `(x,y) = (0,0)`, en distintas posiciones `z`.
- `kl(Tb)` es la conductividad térmica del líquido evaluada a la temperatura
  central.

El coeficiente local de transferencia se obtiene de:

```text
hLocal(z) = q''w(z) / [Tw(z) - Tb(z)]
```

y luego:

```text
NuLocal(z) = hLocal(z) * Dh / kl(Tb(z))
```

Los probes centrales, la temperatura de pared y el flujo de calor se muestrean
con la frecuencia configurada para las capturas VTK. El resultado debe
construirse emparejando cada posición axial `z` y cada tiempo de muestreo.

El cálculo se ejecuta desde la raíz con:

```bash
python3 calculate_nulocal.py
```

El script escribe `postProcessing/NuLocal/<caso>/NuLocal.dat`. Requiere que
las salidas de `centerlineTb`, `wallTemperatureFluid` y `wallHeatFluxFluid`
ya existan y que las dos salidas de pared incluyan la coordenada axial `z`.

