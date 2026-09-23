# Microcanal: geometría y malla

Mallado multirregión desde `geometry/Microcanal.stl`, en milímetros. El STL representa un sólido con sección en I; el fluido ocupa los dos canales laterales.

- Dimensiones exteriores: **0.30 × 0.40 × 10 mm**.
- Referencia inicial: **MC-RC**, canal rectangular del paper.
- Cada franja fluida representa medio canal: **0.075 × 0.30 × 10 mm**.
- `outerLeft` y `outerRight` son planos `symmetryPlane` en x = ±0.15 mm, en ambas regiones.
- Canal físico completo: **0.15 × 0.30 mm**; diámetro hidráulico **Dh = 200 µm**. Las caras de simetría no cuentan como paredes mojadas.
- Regiones: `solid` y `fluid` (ambos canales).

## Generar la malla

Con OpenFOAM y Python 3 disponibles, ejecutar desde la raíz:

```bash
bash AllmeshSTL
```

Verificado con OpenFOAM v2512. El script ejecuta `blockMesh`, `snappyHexMesh`, `topoSet` y `splitMeshRegions`; añade capas en el fluido y lo refina ×2 en dirección transversal x. Reemplaza las mallas anteriores sin archivarlas y guarda los logs en `logs/`.

Se generan inicialmente **3 capas** junto al sólido, con primera capa nominal de **2 µm** y crecimiento **1.25**. El refinamiento posterior subdivide también las capas normales a x.

| Región | Celdas finales |
|---|---:|
| Fluido | 33 600 |
| Sólido | 8 000 |
| **Total** | **41 600** |

Ambas regiones pasan `checkMesh`. El script exige menos de **50 000 celdas** en total.

## Archivos principales

- `system/blockMeshDict`: malla base.
- `system/snappyHexMeshDict` y `system/topoSetDict`: ajuste al STL y selección de regiones.
- `system/fluid/snappyHexMeshDict`: capas de inflación.
- `system/fluid/refineMeshDict`: refinamiento del fluido.
- `constant/fluid/polyMesh` y `constant/solid/polyMesh`: mallas finales.
- `old_geometry/`: diccionarios de la geometría anterior, sin mallas generadas.

## Definición automática de las regiones sólido-fluido

La geometría STL se utiliza para definir directamente la región sólida del dominio. En "snappyHexMeshDict", las celdas ubicadas dentro de la superficie cerrada del STL se asignan a la "cellZone" denominada "solid".

Posteriormente, "topoSet" genera la región "fluid" como el complemento de la región sólida, es decir:

fluid = todas las celdas del dominio - solid

Finalmente, "splitMeshRegions -cellZonesOnly" utiliza las "cellZones" "solid" y "fluid" para generar las mallas independientes:
```
constant/
├── fluid/
│   └── polyMesh/
└── solid/
    └── polyMesh/
```
Esta estrategia permite cambiar fácilmente la geometría sólida sin redefinir manualmente la región fluida. Por ejemplo, el STL puede representar un perfil en T, una sección rectangular, un perfil rectangular hueco u otra geometría cerrada. En todos los casos, el material contenido por el STL se considera sólido y el volumen restante dentro del dominio de "blockMesh" se asigna al fluido.

```

STL
 │
 ▼
snappyHexMesh
 │
 └── cellZone: solid
          │
          ▼
       topoSet
          │
          └── fluid = dominio - solid
                    │
                    ▼
              cellZone: fluid
                    │
                    ▼
        splitMeshRegions
             /          \
          fluid         solid
```

Para que este procedimiento funcione correctamente, la geometría STL debe representar una superficie cerrada y válida, y "locationInMesh" debe encontrarse en una posición coherente con el dominio que se desea conservar.

## Guía de ejecución paso a paso

Para correr la simulación desde cero en OpenFOAM v2512, siga este flujo de trabajo:

### 1. Cargar el entorno de OpenFOAM
Antes de ejecutar cualquier script o comando de OpenFOAM, inicialice las variables de entorno:
```bash
source /usr/lib/openfoam/openfoam2512/etc/bashrc
```

### 2. Generación de la Malla (`AllmeshSTL`)
El script `AllmeshSTL` se encarga del proceso completo de mallado partiendo de la geometría STL (`geometry/Microcanal.stl`):
* Escala la geometría de milímetros a metros (`constant/triSurface/Microcanal_m.stl`).
* Crea la malla base con `blockMesh` y ajusta la superficie sólida con `snappyHexMesh`.
* Separa las regiones con `topoSet` y `splitMeshRegions -cellZonesOnly` creando las carpetas multirregión `constant/fluid/polyMesh` y `constant/solid/polyMesh`.
* Genera las capas límite prismáticas en el fluido y aplica el refinamiento local.
* Verifica las mallas regionales mediante `checkMesh`.

Para ejecutar el mallado:
```bash
bash AllmeshSTL
```

### 3. Ejecución de la Simulación (`AllrunCh`)
`AllrunCh` es el script de lanzamiento (*starter*) del solver **`chtMultiRegionTwoPhaseEulerFoam`**. Verifica la validez de las mallas y ejecuta el cálculo.

* **Ejecución en serie:**
  ```bash
  bash AllrunCh
  ```
* **Ejecución en paralelo (4 núcleos):**
  ```bash
  bash AllrunCh parallel
  ```
  *(Nota: La simulación en paralelo utiliza las configuraciones de `system/decomposeParDict` y los `decomposeParDict` regionales).*

### 4. Pruebas de integración y verificación rápida
Para verificar el funcionamiento de las fuentes de cambio de fase y el solver en la máquina local sin modificar la corrida principal:
```bash
python3 scripts/check_euler.py
```

### 5. Limpieza del caso (`Allclean`)
Para reiniciar el tiempo a 0 y eliminar los directorios de resultados de tiempo y datos de posprocesamiento (conservando las mallas y los archivos de condiciones iniciales en `0/`):
```bash
bash Allclean
```

## Estado del caso

El solver activo es **`chtMultiRegionTwoPhaseEulerFoam` de OpenFOAM v2512**: CHT transitorio, gravedad, dos fases Euler–Euler y evaporación/condensación térmica interfacial. Las fases son `liquid` (agua) y `gas` (vapor de agua). Se conserva silicio, simetría MC-RC, entrada a 300 K y flujo térmico de base de 1 MW/m² (3 W).

La migración está probada con corridas cortas aisladas a 300 K y 380 K. No se ha ejecutado la corrida completa ni validado el modelo contra datos bifásicos. El modelo laminar usa una semilla de vapor y cierres de fase dispersa; **no incluye nucleación de pared**.

El lanzador `AllrunCh` no reconstruye mallas ni restaura campos antiguos. `startFrom startTime` inicia en 0; para una nueva corrida usar una copia limpia de resultados y, para reanudar, configurar explícitamente `startFrom latestTime`. `endTime = 0.0015 s` se conserva como intervalo inicial de prueba, no como tiempo suficiente para establecer el régimen térmico. Los archivos VoF anteriores se conservan en `legacy/vof/` y no son leídos por el solver.

