# Microcanal: geometría y malla

Mallado multirregión desde `geometry/Microcanal.stl`, en milímetros. El STL representa un sólido con sección en I; el fluido ocupa los dos canales laterales.

- Dimensiones exteriores: **0.30 × 0.40 × 5 mm**.
- Referencia inicial: **MC-RC**, canal rectangular del paper.
- Cada franja fluida representa medio canal: **0.075 × 0.30 × 5 mm**.
- `outerLeft` y `outerRight` son planos `symmetryPlane` en x = ±0.15 mm, en ambas regiones.
- Canal físico completo: **0.15 × 0.30 mm**; diámetro hidráulico **Dh = 200 µm**. Las caras de simetría no cuentan como paredes mojadas.
- Regiones: `solid` y `fluid` (ambos canales).

## Generar la malla

Con OpenFOAM y Python 3 disponibles, ejecutar desde la raíz:

```bash
bash AllmeshSTL
```

Verificado con OpenFOAM v2512. El script ejecuta `blockMesh`, `snappyHexMesh`, `topoSet` y `splitMeshRegions`; añade capas en el fluido y lo refina ×2 en dirección transversal x. La caja base usa `32×32×80` divisiones, equivalentes a **81 920 celdas base**. Reemplaza las mallas anteriores sin archivarlas y guarda los logs en `logs/`.

Se generan inicialmente **3 capas** junto al sólido, con primera capa nominal de **2 µm** y crecimiento **1.25**. El refinamiento posterior subdivide también las capas normales a x.

| Región | Celdas finales |
|---|---:|
| Malla base | 81 920 |
| Fluido y sólido | Se informa en `logs/log.checkMesh.*` |
| **Total final** | Se informa en los logs |

Ambas regiones pasan `checkMesh`. Los scripts muestran en los logs la cantidad de celdas de la malla conjunta y el total final por regiones; ya no detienen el proceso por un umbral fijo de celdas.

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
* **Caída de presión (ΔP):** Promedios superficiales `inletFluid` y `outletFluid` en *p* y *p*<sub>rgh</sub> (ΔP = p̅<sub>in</sub> - p̅<sub>out</sub>).
* **Temperatura de la base caliente (T<sub>base</sub>):** Promedio superficial `baseSolid` sobre el parche `outerBottom` (*y* = -0.20 mm, correspondiente a la Fig. 10 del paper).
* **Temperatura media de la pared convectiva (T<sub>W,ave</sub>):** Promedios superficiales `interfaceFluid` e `interfaceSolid` en la interfaz `fluid_to_solid` / `solid_to_fluid`.
* **Temperatura media del fluido (T<sub>f,ave</sub>):** Promedio volumétrico `volFluid` en la región `fluid`.
* **Planos de contorno:** `system/cuttingPlanes` extrae los planos *y* = 0 m (plano medio del canal) y *z* = 5 mm (corte transversal central).
Los resultados se registran automáticamente en el directorio `postProcessing/`.

## Actualización física y de postproceso

- La longitud física y de postproceso es **5 mm**. El área de la base caliente
  es `1.5e-6 m²` y el área convectiva nominal es `4.5e-6 m²`.
- El líquido entra a **300 K** y usa tablas de \(\rho(T)\), \(\mu(T)\),
  \(C_p(T)\) y \(k(T)\) entre 300 y 373.15 K.
- El vapor inicia y entra a **373.15 K**, consistente con la saturación de
  referencia, y usa propiedades tabuladas de transporte y calor específico.
- `constant/fluid/Tsat_water.csv` proporciona \(T_{sat}(p)\) en vez de una
  temperatura de saturación fija.
- `ReDh` se calcula durante la simulación como
  \(Re_{Dh}=\rho(T)|U|D_h/\mu(T)\). `scripts/plot_results.py` lee el campo y
  escribe `plots/reynolds_local.dat` con valores mínimo, medio y máximo.
- El factor de fricción y el número de Nusselt del postproceso usan propiedades
  del líquido dependientes de la temperatura.

El Reynolds de entrada inicial es aproximadamente **60**, no 190.86. El valor
local puede variar espacial y temporalmente durante el calentamiento.

## Estado del caso

El caso se encuentra completamente preparado, verificado y listo para simulación con **`chtMultiRegionTwoPhaseEulerFoam` de OpenFOAM v2512**.

### 1. Física y Formulación del Solver
* **Solver activo:** `chtMultiRegionTwoPhaseEulerFoam` (Transferencia de calor conjugada sólido-fluido multifásica transitoria).
* **Fases interpenetrables:**
  * `liquid`: Agua líquida con propiedades tabuladas dependientes de la temperatura.
  * `gas`: Vapor de agua como gas ideal con propiedades tabuladas de transporte y calor específico.
* **Cambio de fase:** Modelo térmico interfacial (`thermalPhaseChangeTwoPhaseSystem`) con calor latente *L* = 2.26 MJ/kg referenciado a *T<sub>ref</sub>* = 373.15 K y *p<sub>ref</sub>* = 101325 Pa.
* **Fuerzas y acoplamiento interfacial:** Arrastre de Schiller–Naumann, transferencia de calor de Ranz–Marshall, masa virtual (*C<sub>vm</sub>* = 0.5) y diámetro inicial de burbuja/gota de 10 µm.
* **Gravedad:** Activa en dirección transversal *g* = (0, -9.81, 0) m/s².

### 2. Geometría y Materiales
* **Geometría representativa:** Sección en "I" de silicio con 2 medios canales simétricos (*D<sub>h</sub>* = 200 µm, correspondiente al modelo MC-RC de Ghani et al., 2017).
* **Dominio exterior:** 0.30 mm (ancho X) × 0.40 mm (altura Y) × 5.0 mm (longitud Z).
* **Sólido (Silicio):** *k* = 130 W/(m K), *C<sub>p</sub>* = 700 J/(kg K), *ρ* = 2329 kg/m³ (valores experimentales de referencia a 300 K).

### 3. Condiciones de Frontera
* **Entrada de fluido (`inlet`):** Velocidad de entrada de 1.004 m/s, equivalente a un caudal másico de 4.508964 × 10⁻⁵ kg/s de líquido puro (*α<sub>liquid</sub>* = 1) a temperatura *T<sub>in</sub>* = 300 K.
* **Propiedades de referencia a 300 K:** ρ = 998 kg/m³ y μ = 1.002 × 10⁻³ Pa·s.
* **Régimen hidráulico:** Reynolds local con propiedades dependientes de la temperatura; en la entrada a 300 K, **Re<sub>Dₕ</sub> = 200 (laminar)**.

* **Salida de fluido (`outlet`):** Presión estática de 101325 Pa con condición hidrostática `prghPressure`.
* **Base caliente (`outerBottom`):** Flujo de calor uniforme *q''* = 100 W/cm² = 10⁶ W/m² (potencia nominal *Q* ≈ 1.5 W para la longitud de 5 mm).
* **Laterales exteriores (`outerLeft`, `outerRight`):** `symmetryPlane` en ambas regiones.
* **Interfaz sólido-fluido (`solid_to_fluid` / `fluid_to_solid`):** Acoplamiento térmico CHT `compressible::turbulentTemperatureTwoPhaseRadCoupledMixed` con continuidad de flujo de calor y temperatura.
* **Superficies restantes:** Adiabáticas (`zeroGradient`).

### 4. Reducción de Datos y Exportación VTK para Animaciones
* **Integrales numéricas ([system/dataReduction](system/dataReduction)):**
  * ΔP = p̅<sub>in</sub> - p̅<sub>out</sub> (Caída de presión total).
  * T<sub>base</sub> (Temperatura promedio superficial en la base caliente, Fig. 10).
  * T<sub>W,ave</sub> (Temperatura promedio de pared mojada para el cálculo de Nu<sub>ave</sub>).
  * T<sub>f,ave</sub> (Temperatura volumétrica media del fluido).
* **Superficies y planos VTK ([system/cuttingPlanes](system/cuttingPlanes)):**
  * Plano medio longitudinal *y* = 0 m (contornos de velocidad, presión y temperatura).
  * Cortes transversales en *z* = 1.25 mm, *z* = 2.5 mm y *z* = 3.75 mm.
  * Isosuperficie 3D de vapor (*α<sub>gas</sub>* = 0.05) para visualización de burbujas en ParaView.
  * Superficies de pared mojada y base sólida caliente.

### 5. Control Numérico y Estabilidad
* Control temporal efectivo: `deltaT 1e-4 s`, `adjustTimeStep yes`, `maxCo 0.195`, `maxDi 10` y `maxDeltaT 1e-4 s`.
* Frecuencia de escritura: `writeInterval 1e-4 s` con `writeCompression on;` para generar animaciones fluidas optimizando el espacio en disco.
* El caso está validado localmente con el script de prueba de integración `python3 scripts/check_euler.py`.
