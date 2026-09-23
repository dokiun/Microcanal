# Auditoría del caso frente a Ghani et al. (2017)

Fecha: 23 de septiembre de 2026. Alcance: verificación de los archivos actuales, sin modificar la configuración ni ejecutar el solver. Se ejecutó nuevamente `checkMesh -constant -region fluid` y `checkMesh -constant -region solid` con OpenFOAM v2512.

**Actualización posterior — propiedades del sólido:** se sustituyó el cobre por silicio en `constant/solid/thermophysicalProperties`. El resto de este informe conserva el diagnóstico de la configuración anterior. Ahora se usan k = 130 W/(m K), Cp = 700 J/(kg K), rho = 2329 kg/m³ y masa molar = 28.0855 kg/kmol, constantes; Hf = 0 se conserva como referencia de entalpía. El material y la hipótesis de propiedades constantes coinciden con el artículo, pero los valores numéricos no aparecen en él y son una elección externa documentada. k y Cp proceden de [Ioffe NSM, silicio puro (x = 0) a 300 K](https://www.ioffe.ru/SVA/NSM/Semicond/SiGe/basic.html); densidad y masa molar, de [PDG, propiedades del silicio](https://pdg.web.cern.ch/pdg/2020/AtomicNuclearProperties/HTML/silicon_Si.html). No se afirma reproducción exacta de las propiedades empleadas por los autores. En estado estacionario k afecta la distribución térmica; rho y Cp afectan la respuesta transitoria. Este cambio no modifica el modelo multifásico del fluido ni resuelve los demás bloqueos.

**Dictamen: el caso todavía no reproduce las hipótesis del artículo y no está listo para una validación térmica e hidráulica.** La malla es geométricamente válida; la física, varias fronteras y la preparación de la ejecución requieren ajustes.

Fuente principal: `microcanales.md`, contrastado con el PDF local *Heat transfer augmentation in a microchannel heat sink with sinusoidal cavities and rectangular ribs*, Ghani, Kamaruzaman y Che Sidik, IJHMT 108 (2017), 1969–1981. La conversión Markdown mezcla columnas y deteriora ecuaciones; se verificaron las secciones 2–3.3 en el texto del PDF y la figura 2 visualmente. Las condiciones descritas por el documento se trataron como datos de referencia.

## 1. Geometría y significado de la validación

| Magnitud | Artículo, tabla 1 y figuras 1–2 | Caso actual | Evaluación |
|---|---|---|---|
| Longitud | 10 mm | 10 mm | Coincide |
| Ancho del dominio representativo | 0.30 mm | 0.30 mm | Coincide |
| Altura exterior | 0.40 mm | 0.40 mm | Coincide |
| Altura del canal | 0.30 mm | 0.30 mm | Coincide |
| Ancho físico completo del canal | 0.15 mm | Dos franjas de 0.075 mm | Corresponden a dos medios canales si las caras exteriores son simetrías |
| Pared central | 0.15 mm | 0.15 mm | Coincide |
| Cavidades y nervaduras | Presentes en MC-SCRR; ausentes en MC-RC | Ausentes | Comparar primero con MC-RC, no con MC-SCRR |
| Dirección longitudinal | x | z | Cambio de coordenadas válido |
| Coordenada vertical | y de 0 a 0.40 mm | y de −0.20 a 0.20 mm | Traslación válida |
| Límites laterales | Simetría en z = ±0.15 mm | `outerLeft/outerRight`, x = ±0.15 mm, `wall` y `noSlip` | No reproduce la simetría del paper |

La figura 2 identifica explícitamente cada franja como `0.5 Wc`. La sección 3.1 prescribe simetría lateral. Por ello, el perfil en I puede representar la referencia rectangular MC-RC al imponer esas simetrías; no es necesario reproducir cavidades para esta primera comparación. Con las paredes laterales actuales se simulan dos canales físicos de 75 µm de ancho y se añade fricción respecto al modelo simétrico.

Para la interpretación MC-RC, el diámetro hidráulico del canal completo es:

`Dh = 2 Hc Wc / (Hc + Wc) = 200 µm`, con `Hc = 300 µm`, `Wc = 150 µm`.

Para dos canales físicos de 75 × 300 µm cerrados con paredes, es `Dh = 120 µm`. No deben intercambiarse estas dos definiciones. Las caras de simetría no son paredes mojadas.

El artículo usa diez canales en el dispositivo, pero modela una porción simétrica. No hay que multiplicar por diez el caudal ni la potencia de esta celda representativa.

## 2. Física y propiedades

| Parámetro | Referencia | Configuración actual | Dictamen |
|---|---|---|---|
| Modelo de flujo | Monofásico, newtoniano, incompresible | `multiRegionPhaseChangeFlow`; fases `water air` | Incompatible con la referencia |
| Régimen | Laminar, Re entre 100 y 800 | `simulationType laminar` | Coincide el modelo; falta fijar el Re objetivo |
| Estado | Estacionario | Esquemas `backward` regionales y PIMPLE | Transitorio; solo comparable tras demostrar estado estacionario |
| Propiedades | Constantes | Agua con EOS `Boussinesq` | Densidad dependiente de T; no coincide |
| Sólido | Silicio | Cobre: k = 401 W/(m K), Cp = 385 J/(kg K), rho = 8960 kg/m³ | No coincide; k altera directamente el resultado estacionario |
| Gravedad | Despreciada | `g = (0 -9.81 0)` y `accelerationForceModel gravity` | No coincide |
| Radiación | Despreciada | Sólido `radiationModel none`; interfaces `qr/qrNbr none` | Compatible con lo declarado |
| Disipación viscosa | Despreciada | No se dispone aquí del código del solver personalizado | No corroborable solo con estos diccionarios |
| Cambio de fase | No forma parte del modelo | `implicitGrad`, `hardtWondra`, `directEvaporation`, `superheated 1` | Configuración ajena al paper |

Archivos: `constant/fluid/{thermophysicalProperties,thermophysicalProperties.water,thermophysicalProperties.air,phaseChangeProperties,turbulenceProperties}`, `constant/solid/{thermophysicalProperties,radiationProperties}`, `constant/g`, `system/controlDict`.

El agua tiene `rho0 = 958.4 kg/m³`, `T0 = 373.15 K`, `beta = 6.9e-4 K⁻¹`, `mu = 2.8176e-4 Pa s`, `Cp = 4216 J/(kg K)` y `Pr = 1.7703430104321904`. Para el transporte constante, `k = mu Cp / Pr = 0.671 W/(m K)`. La EOS da `rho(300 K) = 1006.7738 kg/m³`: cambiar solamente la temperatura inicial a 300 K no transforma este conjunto en propiedades constantes de agua a esa temperatura.

La fase denominada `air` tiene masa molar 18.015, Cp = 2030, Hf = 2.257e6 J/kg, mu = 1.22e-5 Pa s, Pr = 1 y gas ideal: el nombre es engañoso, pues está parametrizada como vapor de agua. En cambio de fase figuran Tsat = 373.15 K, psat = 101235 Pa, L = 2.26e6 J/kg y límites 200–500 K. La presión de saturación difiere de los 101325 Pa de salida; estos parámetros no corresponden a la validación monofásica.

Otros controles multifásicos: sigma = 0.059 N/m, pMin = 20000 Pa y límites térmicos 100–500 K. No tienen equivalentes que deban reproducirse del paper; son controles del modelo actual. `alpha.water = 1` inicialmente no elimina las ecuaciones de segunda fase ni desactiva por sí mismo evaporación.

**Límite documental:** no se encontró en el artículo adjunto una tabla con valores numéricos de rho, mu, Cp, k del refrigerante o k del silicio. Tampoco se identificó una declaración inequívoca del refrigerante en la descripción del método; las menciones a agua en referencias bibliográficas no bastan para establecerla. El caso usa agua, pero no se debe atribuir al paper un conjunto concreto de propiedades de agua a 300 K. Para reproducción cuantitativa, hay que declarar una fuente externa y la temperatura de evaluación, o recuperar esos datos de los autores. El material silicio sí está explícitamente indicado.

## 3. Condiciones iniciales y de frontera

| Campo/frontera | Actual | Comparación y acción necesaria |
|---|---|---|
| `0/fluid/U`, entrada | `flowRateInletVelocity`, caudal total 1.21e-5 kg/s, `extrapolateProfile yes` | El paper impone velocidad axial uniforme. Calcularla desde Re y usar perfil uniforme; el caudal pertenece a todo el patch, no a cada mitad |
| U inicial | (0 0 0.27) m/s | Dirección correcta; el valor inicial no sustituye al caudal impuesto |
| U salida | `pressureInletOutletVelocity` | Condición abierta compatible en principio; comprobar ausencia de retroflujo y dependencia del solver |
| U interfaz sólido-fluido | `noSlip` | Coincide |
| U laterales exteriores | `noSlip` | Cambiar a simetría si se busca MC-RC |
| `T` y `T.water` entrada/inicial | 300 K | Coincide con Tin del paper |
| `T.air` entrada/inicial | 372.15 K | Inconsistente con inicialización a 300 K; campo ajeno al objetivo monofásico |
| Temperatura salida | `zeroGradient` | Coincide con gradiente axial nulo |
| `0/fluid/T` laterales | No hay entradas `outerLeft` ni `outerRight` | Campo incompleto frente a la malla: impide leer T si el solver lo requiere |
| `T.water/T.air` laterales | `zeroGradient` | Gradiente térmico normal nulo; no corrige la condición mecánica `noSlip` |
| `0/solid/T`, base | `externalWallHeatFluxTemperature`, modo flux, q = 1e6 W/m² | Coincide: 100 W/cm² = 1e6 W/m² |
| Sólido: techo, entrada y salida | `zeroGradient` | Coincide con superficies adiabáticas |
| Sólido: lados | `zeroGradient` | Compatible térmicamente con simetría para un escalar; al adaptar la malla, usar campos consistentes con `symmetryPlane` |
| T en interfaces | `compressible::turbulentTemperatureRadCoupledMixed`, `Tnbr T`, conductividad fluidThermo/solidThermo | Intención CHT correcta. En bifásico hay T, T.water y T.air; debe verificarse qué temperatura y conductividad usa el solver. El nombre de la BC no obliga a usar turbulencia |
| Presión inicial | 101325 Pa | Referencia de 1 atm correcta |
| `p` y `p_rgh` salida | `totalPressure`, p0 = 101325 Pa | No es una prescripción incondicional de presión estática; véase matiz siguiente |
| Presión entrada | `zeroGradient` | Revisar con la ecuación de presión del solver elegido, especialmente al usar p_rgh y gravedad |
| Presión paredes | `fixedFluxPressure` | BC habitual para compatibilidad de flujo, pero su uso efectivo depende de qué presión resuelva el solver |

En OpenFOAM v2512, `totalPressure` con `psi none` aplica `p = p0 - 0.5 rho neg(phi) |U|²`. En salida pura (`phi > 0`), resulta p = p0; con retroflujo cambia. Por tanto no es correcto afirmar que resta siempre la presión dinámica. Además `p_rgh = p - rho gh`: imponer el mismo valor a p y p_rgh con gravedad requiere revisar la reconstrucción hidrostática. Para la referencia sin gravedad, se simplifica usando g = 0 y la condición de presión correspondiente al solver.

Potencia nominal de la base: `A_base = 0.0003 × 0.01 = 3e-6 m²`, `Q = q A_base = 3 W`. La interfaz sólido-fluido de la geometría rectangular tiene área nominal `9e-6 m²`; no confundirla con el área calentada. Con el caudal y Cp actuales, un balance estacionario sin pérdidas da `Tout_bulk - Tin = 3/(1.21e-5 × 4216) = 58.81 K`. Es una estimación de balance, no un resultado CFD ni una predicción del paper.

## 4. Reynolds y caudal

Área total de entrada de las dos franjas: `A = 2 × 75e-6 × 300e-6 = 4.5e-8 m²`.

Con el caudal actual y líquido ocupando toda la entrada:

`Umedia = mdot/(rho A) ≈ 0.26708 m/s` usando la EOS actual a 300 K.

`Re = rho Umedia Dh/mu = mdot Dh/(mu A)`.

- Con las paredes actuales, Dh = 120 µm: **Re ≈ 114.52**.
- Con la interpretación simétrica del paper, Dh = 200 µm: **Re ≈ 190.86**.

Aunque ambos están dentro de 100–800, no equivalen a un punto declarado del barrido ni permiten comparar resultados sin resolver la condición lateral. Estos números usan la viscosidad actual; al reemplazarla, cambia Re si se conserva el caudal.

Para reproducir MC-RC con propiedades constantes elegidas explícitamente:

`Uin = Re mu/(rho × 2e-4)`; `mdot_total = Re mu × 2.25e-4` (unidades SI).

| Re | mdot_total / mu (m) | Uin / (mu/rho) (1/m) |
|---|---:|---:|
| 100 | 0.0225 | 500000 |
| 200 | 0.0450 | 1000000 |
| 300 | 0.0675 | 1500000 |
| 400 | 0.0900 | 2000000 |
| 500 | 0.1125 | 2500000 |
| 600 | 0.1350 | 3000000 |
| 700 | 0.1575 | 3500000 |
| 800 | 0.1800 | 4000000 |

Esta tabla evita inventar propiedades ausentes del artículo. Las dos mitades reciben nominalmente la mitad del caudal total cuando la solución es simétrica.

## 5. Solución numérica y tiempo

El paper usa FLUENT 14, SIMPLE, convección upwind de segundo orden y difusión central de segundo orden. Declara residuos inferiores a 1e-6 en continuidad y 1e-9 en energía (sección 3.2).

El caso actual utiliza:

- PIMPLE regional: 4 correctores exteriores, 5 de presión y 2 no ortogonales; predictor de momento activo. El diccionario global tiene 2 correctores y 0 no ortogonales. Qué controles se consumen debe comprobarse en el solver personalizado.
- Convección de U `linearUpwind`, interpolación lineal, gradientes limitados y difusión con corrección limitada 0.80. Son opciones razonables de discretización, pero no equivalentes exactos de todos los esquemas de FLUENT.
- En varios términos escalares se usa `linearUpwind grad(U)`: en la implementación local, ese nombre selecciona el esquema de gradiente aplicado al campo transportado. No demuestra por sí solo un error de tipo vector/escalar, pero comparte el esquema de U y conviene especificar `grad(T)`, `grad(h)` o el campo correspondiente para claridad y control.
- Presión: tolerancia 1e-6, final 1e-7. U/energía/temperaturas: 1e-7, final 5e-8. Sólido: 1e-8. `residualControl` pide p = 1e-4, U = 1e-5, h = 1e-4 y no nombra p_rgh ni T.water/T.air. No reproduce el criterio térmico 1e-9 del paper.
- Las tolerancias de los solucionadores lineales no equivalen automáticamente a los residuos globales de FLUENT. Deben verificarse también convergencia entre iteraciones, balances y estabilización de observables.
- Relajación: p/p_rgh 0.72, rho 0.80; h 0.80, T 0.70, U 0.87, alpha 0.5. No hay valores equivalentes documentados en el paper.
- `startFrom latestTime`, `endTime 0.0015 s`, deltaT inicial 1e-8 s, máximo 5e-7 s, ajuste temporal activo, Co y alphaCo máximos 0.195, Di máximo 50 y número capilar máximo 1. Son controles transitorios, varios exclusivos de multifase.
- Escritura cada 1e-4 s, formato binario, precisión 8 y sin purga. No determinan concordancia física.

A la velocidad actual, el tiempo de tránsito es aproximadamente `L/U = 0.03744 s`; el final configurado, 0.0015 s, representa apenas 4 % de ese tiempo. Esto no constituye una demostración de estado estacionario. Un solver transitorio podría alcanzar la referencia, pero necesita una duración determinada por convergencia real, no por el límite actual.

Para el objetivo del paper, `chtMultiRegionSimpleFoam` es un candidato estacionario instalado en v2512. Adoptarlo requiere adaptar conjuntamente termofísica, campos, BC, ecuaciones y diccionarios; cambiar solo `application` no basta. Hay que verificar que la ecuación de energía elegida respete las simplificaciones del artículo.

## 6. Malla, interfaz y posproceso

Se corroboró con una nueva ejecución de `checkMesh`:

| Región | Celdas | Volumen | No ortogonalidad máxima | Skewness máximo | Resultado |
|---|---:|---:|---:|---:|---|
| Fluido | 33600 | 4.5e-10 m³ | 36.21° | 2.0214 | Mesh OK |
| Sólido | 8000 | 7.5e-10 m³ | ≈ 0° | ≈ 0 | Mesh OK |

El fluido tiene dos componentes desconectadas, coherentes con las dos franjas. Cada componente necesita referencia de presión; ambas tocan el patch de salida común. La interfaz está declarada como `mappedWall` recíproco, `nearestPatchFace`, con 5600 caras fluidas y 4000 sólidas. La diferencia de conteos no implica por sí sola error; sí exige verificar conservación de calor al acoplar las mallas.

La malla base es 8 × 8 × 200. Se configuran 3 capas fluidas en la interfaz, primera nominal de 2 µm y crecimiento 1.25; después se refina en x por factor 2. El total es 41600 celdas. El límite de 50000 pertenece al proyecto, no al artículo.

El paper adopta 1.021 millones de celdas tras un estudio de independencia para MC-SCRR, Re = 600. Esa cifra no es un requisito transferible al canal recto. Tampoco basta `Mesh OK` para acreditar independencia: deben compararse al menos tres resoluciones con Δp, Nu y temperaturas. Los valores Nu = 19.646238 y Δp = 54458.9185 Pa de la tabla 2 pertenecen a MC-SCRR; no son objetivos válidos para este canal recto.

`system/probes` conserva coordenadas antiguas: las sondas fluidas x = y = 150 µm están sobre una esquina de la frontera; las sondas supuestamente sólidas x = 150 µm, y = 25 µm están junto al fluido, fuera del volumen sólido interior. Los planos x = 150 µm e y = 150 µm son fronteras o interfaces, no planos medios. Deben recolocarse; por ejemplo, sondas interiores del fluido en x = ±112.5 µm, y = 0, y de la base sólida en y = −175 µm. Las etiquetas sobre secciones adiabáticas/calentadas del caso anterior tampoco representan la base actual, calentada en toda su longitud.

No hay funciones activas para balance de masa/calor, Δp, temperatura bulk, Nu ni factor de fricción. Se necesitan antes de afirmar validación. Según ecuaciones 8–12 del paper:

`f_app = 2 Dh Δp/(Lt rho Umedia²)` (convención de Darcy), `Po = f_app Re`.

`h_ave = q A_film/[A_con (Tw_ave - Tf_ave)]`; `Nu_ave = h_ave Dh/kf`.

Documentar superficies y ponderaciones de cada promedio: la temperatura bulk ponderada por flujo de entalpía sirve para el balance energético; no se debe suponer sin comprobación que coincide con toda definición de temperatura media del artículo. Evitar comparar factores de Darcy con Fanning (factor 4). Para MC-RC, usar sección 4.1/figura 4 y correlaciones dentro de sus hipótesis y región de desarrollo.

## 7. Preparación y bloqueos de ejecución

- `AllrunCh` intenta copiar `system/fluid/blockMeshDict` y `system/solid/blockMeshDict`, que no existen, y utiliza `restore0Dir` sin una carpeta `0.orig` presente. Es un flujo antiguo, no un lanzador válido para la geometría actual.
- Los tres `decomposeParDict` fijan 4 subdominios; `AllrunCh` lanza MPI con 10 procesos. Deben concordar.
- `AllmeshSTL` genera y comprueba la malla; no convierte el caso físico ni actualiza todas las BC.
- `multiRegionPhaseChangeFlow` no fue encontrado en PATH tras cargar el entorno v2512. No se descarta una instalación externa en otro entorno, pero no está disponible en el entorno comprobado. Los solvers CHT estándar sí están instalados.
- `setFieldsDict` e `initAlphaFieldDict` contienen una separación en y = 300 µm, fuera del rango fluido actual ±150 µm; su intención de crear vapor ya no es pertinente. `setFieldTableDict` referencia `T01.csv`, ausente. Estos archivos no actúan por su mera presencia; dependen de que se ejecuten sus utilidades.
- `startFrom latestTime` puede reanudar resultados previos en lugar del estado 0. Para un caso de validación reproducible, fijar explícitamente el inicio y registrar el conjunto de propiedades y Re utilizado.
- El README menciona preparación pendiente para `chtMultiRegionFoam`, pero `controlDict` selecciona otro solver. El diccionario es la evidencia de la aplicación configurada.

## 8. Orden de corrección propuesto

1. Adoptar MC-RC como referencia inicial y convertir las caras laterales en simetría, tanto en malla como en campos y generadores. Si se conservan como paredes físicas, declarar esa geometría diferente y usar su propio Dh y referencia de validación.
2. Elegir un modelo monofásico CHT estacionario, sin gravedad ni cambio de fase; definir propiedades constantes del refrigerante y del silicio con fuente explícita.
3. Seleccionar el Re inicial y calcular velocidad/caudal con esas propiedades. Conservar Tin = 300 K, salida a 1 atm, flujo de base 1e6 W/m² y exteriores adiabáticos.
4. Completar campos y revisar el acoplamiento térmico, la ecuación de presión, la energía y los criterios de convergencia del solver seleccionado.
5. Reparar el lanzador, recolocar sondas y añadir balances y magnitudes de validación. Comprobar arranque en una copia del caso.
6. Ejecutar hasta convergencia, verificar Q ≈ 3 W y balance de entalpía, estudiar independencia de malla y contrastar MC-RC. Solo después extender la comparación al barrido de Re.

## Fuentes técnicas complementarias

- [OpenCFD: Boussinesq](https://doc.openfoam.com/2306/tools/processing/models/thermophysical/equation-of-state/rtm/Boussinesq/): dependencia de densidad con temperatura.
- [OpenCFD: flowRateInletVelocity](https://doc.openfoam.com/2306/tools/processing/boundary-conditions/rtm/derived/inlet/flowRateInletVelocity/): caudal integral y extrapolación del perfil.
- [OpenCFD: linearUpwind](https://doc.openfoam.com/2312/tools/processing/numerics/schemes/divergence/rtm/linearUpwind/): esquema de convección.
- Código instalado v2512: `src/finiteVolume/fields/fvPatchFields/derived/totalPressure/totalPressureFvPatchScalarField.C` y `src/finiteVolume/interpolation/surfaceInterpolation/schemes/linearUpwind/linearUpwind.C`, inspeccionados para matizar comportamiento de presión y selección del gradiente.

No se generaron resultados de flujo o temperatura; este informe verifica preparación y correspondencia, no certifica una simulación validada.
