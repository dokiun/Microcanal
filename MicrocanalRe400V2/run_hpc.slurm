#!/bin/bash
#SBATCH --job-name=microchannelRe400
#SBATCH --partition=hpc-long
#SBATCH --time=48:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

set -eo pipefail

cd "${SLURM_SUBMIT_DIR}/MicrocanalRe400"
module load openfoam/2506
set +e
set +u
source "$WM_PROJECT_DIR/etc/bashrc"
source_status=$?
set -u
set -e
if [[ "$source_status" -ne 0 ]]; then
    echo "Aviso: etc/bashrc terminó con estado $source_status; se validarán los comandos." >&2
fi
set -u

for command_name in chtMultiRegionTwoPhaseEulerFoam checkMesh decomposePar; do
    command -v "$command_name" >/dev/null || exit 1
done

echo "Nodo: $(hostname)"
echo "Trabajo: ${SLURM_JOB_ID}"
echo "Directorio: ${PWD}"
echo "Tareas: ${SLURM_NTASKS}"

checkMesh -constant -region fluid
checkMesh -constant -region solid

decomposePar -allRegions -force

mpirun -np "${SLURM_NTASKS}" chtMultiRegionTwoPhaseEulerFoam -parallel
