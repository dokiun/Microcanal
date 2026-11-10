#!/usr/bin/env python3
"""Prepara el mallado a partir del STL (sólido). Todo se calcula del STL:
   - convierte el STL a metros (constant/triSurface/Microcanal_m.stl)
   - system/blockMeshDict : caja = bounding box del STL, celdas ~ CELL (malla base uniforme)
   - system/meshParams    : locationInMesh y parámetros de capas
"""
import struct, re
import numpy as np

# ------------------------- PARÁMETROS (lo único que tocas) -------------------------
STL_IN  = "geometry/Microcanal.stl"
STL_OUT = "constant/triSurface/Microcanal_m.stl"
SCALE   = 1e-3                           # unidades del STL -> metros (mm -> m)
CELL    = (6.25e-6, 6.25e-6, 31.25e-6)   # tamaño objetivo de celda base en x,y,z (m)
N_LAYERS      = 5                        # capas en el FLUIDO pegadas a la interfaz con el sólido
FIRST_LAYER   = 0.20                     # espesor 1.ª capa, RELATIVO al tamaño de celda base
EXPANSION     = 1.3                      # razón de crecimiento de las capas
# ------------------------------------------------------------------------------------

def read_stl(path):
    d = open(path, "rb").read()
    if d[:5] == b"solid" and b"facet" in d[:1000]:                      # ASCII
        v = re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", d)
        return np.array(v, dtype=float).reshape(-1, 3, 3)
    n = struct.unpack("<I", d[80:84])[0]                                # binario
    t = np.frombuffer(d[84:84 + 50*n], dtype=np.dtype([("n","<3f4"),("v","<9f4"),("a","<u2")]))
    return t["v"].astype(float).reshape(-1, 3, 3)

tri = read_stl(STL_IN) * SCALE
lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
lo, hi = np.round(lo, 12), np.round(hi, 12)

with open(STL_OUT, "w") as f:                                           # STL en metros
    f.write("solid Microcanal\n")
    for t in tri:
        nrm = np.cross(t[1]-t[0], t[2]-t[0]); nn = np.linalg.norm(nrm)
        nrm = nrm/nn if nn > 0 else nrm
        f.write(f" facet normal {nrm[0]:.9g} {nrm[1]:.9g} {nrm[2]:.9g}\n  outer loop\n")
        for p in t: f.write(f"   vertex {p[0]:.12g} {p[1]:.12g} {p[2]:.12g}\n")
        f.write("  endloop\n endfacet\n")
    f.write("endsolid Microcanal\n")

n = [max(1, int(round((hi[i]-lo[i])/CELL[i]))) for i in range(3)]
x0,y0,z0 = lo; x1,y1,z1 = hi
bm = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  plus                                  |
|   \\  /    A nd           | Web:      www.OpenFOAM.com                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

// GENERADO por prepMesh.py desde el STL. No editar a mano.
convertToMeters 1;
vertices
(
    ({x0:.12g} {y0:.12g} {z0:.12g}) ({x1:.12g} {y0:.12g} {z0:.12g}) ({x1:.12g} {y1:.12g} {z0:.12g}) ({x0:.12g} {y1:.12g} {z0:.12g})
    ({x0:.12g} {y0:.12g} {z1:.12g}) ({x1:.12g} {y0:.12g} {z1:.12g}) ({x1:.12g} {y1:.12g} {z1:.12g}) ({x0:.12g} {y1:.12g} {z1:.12g})
);
blocks ( hex (0 1 2 3 4 5 6 7) ({n[0]} {n[1]} {n[2]}) simpleGrading (1 1 1) );
edges ();
boundary
(
    inlet       {{ type patch;         faces ((0 3 2 1)); }}
    outlet      {{ type patch;         faces ((4 5 6 7)); }}
    outerBottom {{ type wall;          faces ((0 1 5 4)); }}
    outerRight  {{ type symmetryPlane; faces ((1 2 6 5)); }}
    outerTop    {{ type wall;          faces ((2 3 7 6)); }}
    outerLeft   {{ type symmetryPlane; faces ((3 0 4 7)); }}
);
mergePatchPairs ();
"""
open("system/blockMeshDict", "w").write(bm)

d = (hi-lo)/n                                    # punto interior: centro, fuera de las caras de celda
loc = (lo+hi)/2 + d*np.array([0.137, 0.211, 0.317])
mp = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  plus                                  |
|   \\  /    A nd           | Web:      www.OpenFOAM.com                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      meshParams;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

// GENERADO por prepMesh.py
locationInMesh ({loc[0]:.9g} {loc[1]:.9g} {loc[2]:.9g});
nLayers      {N_LAYERS};
firstLayer   {FIRST_LAYER};
expansion    {EXPANSION};
"""
open("system/meshParams", "w").write(mp)

print(f"STL: {lo} -> {hi}  (m)")
print(f"Malla base uniforme: {n[0]} x {n[1]} x {n[2]} = {n[0]*n[1]*n[2]} celdas  (celda {d[0]*1e6:.2f} x {d[1]*1e6:.2f} x {d[2]*1e6:.2f} um)")
