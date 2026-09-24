#!/usr/bin/env python3
"""Run isolated cold/hot one-step integration checks with the loaded OpenFOAM."""
from pathlib import Path
import math
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOLVER = 'chtMultiRegionTwoPhaseEulerFoam'

def check(case, temperature):
    text = (case / 'system/controlDict').read_text()
    for key, value in [('endTime', '1e-8'), ('deltaT', '1e-8'), ('writeInterval', '1e-8'), ('adjustTimeStep', 'no')]:
        text = re.sub(rf'\b{key}\s+[^;]+;', f'{key} {value};', text)
    (case / 'system/controlDict').write_text(text)
    for relative in ['0/fluid/T.liquid', '0/fluid/T.gas', '0/solid/T']:
        path = case / relative
        path.write_text(path.read_text().replace('uniform 300', f'uniform {temperature}'))
    with (case / 'solver.log').open('w') as log:
        subprocess.run([SOLVER, '-case', str(case)], stdout=log, stderr=subprocess.STDOUT, check=True)
    log = (case / 'solver.log').read_text()
    assert re.search(r'^End$', log, re.M), 'Solver did not finish'
    assert 'FOAM FATAL' not in log
    assert 'FOAM Warning' not in log, 'Inspect solver warnings'
    transfers = [float(x) for x in re.findall(r'iDmdt.gasAndLiquid:.*?integral = (\S+)', log)]
    assert transfers and all(math.isfinite(x) for x in transfers)
    assert transfers[-1] < 0 if temperature < 373.15 else transfers[-1] > 0
    bounds = re.findall(r'Min\(alpha1\) = (\S+)  Max\(alpha1\) = (\S+)', log)
    assert bounds and all(0 <= float(lo) <= float(hi) <= 1 for lo, hi in bounds)
    print(f'{temperature} K: PASS; integrated gas source = {transfers[-1]:.6g} kg/s; {case}', flush=True)

if __name__ == '__main__':
    if not shutil.which(SOLVER):
        raise SystemExit('Load OpenFOAM v2512 before running this script.')
    work = Path(tempfile.mkdtemp(prefix='microcanal-euler-check-'))
    print(f'Validation output: {work}', flush=True)
    for temperature in [300, 380]:
        case = work / str(temperature)
        case.mkdir()
        for name in ['0', 'constant', 'system']:
            shutil.copytree(ROOT / name, case / name)
        check(case, temperature)
