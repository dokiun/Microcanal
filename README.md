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

### 6. Reducción de datos e integrales superficiales (Ghani et al., 2017)
El caso evalúa automáticamente en cada paso de tiempo las variables integrales del artículo mediante el diccionario [system/dataReduction](system/dataReduction):
* **Caída de presión ($\Delta P$):** Promedios superficiales `inletFluid` y `outletFluid` en $p$ y $p_{rgh}$ ($\Delta P = \bar{p}_{in} - \bar{p}_{out}$).
* **Temperatura de la base caliente ($T_{base}$):** Promedio superficial `baseSolid` sobre el parche `outerBottom` ($y = -0.20\text{ mm}$, correspondiente a la Fig. 10 del paper).
* **Temperatura media de la pared convectiva ($T_{W,ave}$):** Promedios superficiales `interfaceFluid` e `interfaceSolid` en la interfaz `fluid_to_solid` / `solid_to_fluid`.
* **Temperatura media del fluido ($T_{f,ave}$):** Promedio volumétrico `volFluid` en la región `fluid`.
* **Planos de contorno:** `system/cuttingPlanes` extrae los planos $y = 0\text{ m}$ (plano medio del canal) y $z = 5\text{ mm}$ (corte transversal central).
Los resultados se registran automáticamente en el directorio `postProcessing/`.

## Estado del caso

El caso se encuentra completamente preparado, verificado y listo para simulación con **`chtMultiRegionTwoPhaseEulerFoam` de OpenFOAM v2512**.

### 1. Física y Formulación del Solver
* **Solver activo:** `chtMultiRegionTwoPhaseEulerFoam` (Transferencia de calor conjugada sólido-fluido multifásica transitoria).
* **Fases interpenetrables:**
  * `liquid`: Agua líquida con ecuación de estado Boussinesq ($C_p = 4216\text{ J/(kg K)}$, $k = 0.671\text{ W/(m K)}$, $\mu = 2.82 \times 10^{-4}\text{ Pa s}$).
  * `gas`: Vapor de agua como gas ideal ($C_p = 2030\text{ J/(kg K)}$, $k = 0.0248\text{ W/(m K)}$, $\mu = 1.22 \times 10^{-5}\text{ Pa s}$).
* **Cambio de fase:** Modelo térmico interfacial (`thermalPhaseChangeTwoPhaseSystem`) con calor latente $L = 2.26\text{ MJ/kg}$ referenciado a $T_{ref} = 373.15\text{ K}$ y $p_{ref} = 101325\text{ Pa}$.
* **Fuerzas y acoplamiento interfacial:** Arrastre de Schiller–Naumann, transferencia de calor de Ranz–Marshall, masa virtual ($C_{vm} = 0.5$) y diámetro inicial de burbuja/gota de $10\ \mu\text{m}$.
* **Gravedad:** Activa en dirección transversal $g = (0, -9.81, 0)\text{ m/s}^2$.

### 2. Geometría y Materiales
* **Geometría representativa:** Sección en "I" de silicio con 2 medios canales simétricos ($D_h = 200\ \mu\text{m}$, correspondiente al modelo MC-RC de Ghani et al., 2017).
* **Dominio exterior:** $0.30\text{ mm (ancho X)} \times 0.40\text{ mm (altura Y)} \times 10.0\text{ mm (longitud Z)}$.
* **Sólido (Silicio):** $k = 130\text{ W/(m K)}$, $C_p = 700\text{ J/(kg K)}$, $\rho = 2329\text{ kg/m}^3$ (valores experimentales de referencia a 300 K).

### 3. Condiciones de Frontera
* **Entrada de fluido (`inlet`):** Caudal másico constante de $1.21 \times 10^{-5}\text{ kg/s}$ de líquido puro ($\alpha_{liquid} = 1$) a temperatura $T_{in} = 300\text{ K}$.
* **Salida de fluido (`outlet`):** Presión estática de $101325\text{ Pa}$ con condición hidrostática `prghPressure`.
* **Base caliente (`outerBottom`):** Flujo de calor uniforme $q'' = 100\text{ W/cm}^2 = 10^6\text{ W/m}^2$ (potencia nominal $Q = 3\text{ W}$ en el dominio representativo).
* **Laterales exteriores (`outerLeft`, `outerRight`):** `symmetryPlane` en ambas regiones.
* **Interfaz sólido-fluido (`solid_to_fluid` / `fluid_to_solid`):** Acoplamiento térmico CHT `compressible::turbulentTemperatureTwoPhaseRadCoupledMixed` con continuidad de flujo de calor y temperatura.
* **Superficies restantes:** Adiabáticas (`zeroGradient`).

### 4. Reducción de Datos y Exportación VTK para Animaciones
* **Integrales numéricas ([system/dataReduction](system/dataReduction)):**
  * $\Delta P = \bar{p}_{in} - \bar{p}_{out}$ (Caída de presión total).
  * $T_{base}$ (Temperatura promedio superficial en la base caliente, Fig. 10).
  * $T_{W,ave}$ (Temperatura promedio de pared mojada para el cálculo de $\text{Nu}_{ave}$).
  * $T_{f,ave}$ (Temperatura volumétrica media del fluido).
* **Superficies y planos VTK ([system/cuttingPlanes](system/cuttingPlanes)):**
  * Plano medio longitudinal $y = 0\text{ m}$ (contornos de velocidad, presión y temperatura).
  * Cortes transversales en $z = 2.5\text{ mm}$, $z = 5.0\text{ mm}$ y $z = 7.5\text{ mm}$.
  * Isosuperficie 3D de vapor ($\alpha_{gas} = 0.05$) para visualización de burbujas en ParaView.
  * Superficies de pared mojada y base sólida caliente.

### 5. Control Numérico y Estabilidad
* Paso de tiempo adaptativo con $\text{maxCo} = 0.195$, $\text{maxDi} = 10$, $\Delta t_{inicial} = 10^{-8}\text{ s}$ y $\Delta t_{max} = 5 \times 10^{-7}\text{ s}$.
* Frecuencia de escritura: `writeInterval 1e-4 s` con `writeCompression on;` para generar animaciones fluidas optimizando el espacio en disco.
* El caso está validado localmente con el script de prueba de integración `python3 scripts/check_euler.py`.
