#!/bin/bash
#SBATCH --job-name=microchannelRe400
#SBATCH --partition=hpc-long
#SBATCH --time=72:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=7
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --output=logs/slurm-%x-%j.out
#SBATCH --error=logs/slurm-%x-%j.err

set -eo pipefail

cd "${SLURM_SUBMIT_DIR}"
mkdir -p logs
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

for command_name in chtMultiRegionFoam checkMesh decomposePar; do
    command -v "$command_name" >/dev/null || exit 1
done

echo "Nodo: $(hostname)"
echo "Trabajo: ${SLURM_JOB_ID}"
echo "Directorio: ${PWD}"
echo "Tareas: ${SLURM_NTASKS}"

checkMesh -constant -region fluid > logs/log.checkMesh.fluid 2>&1
checkMesh -constant -region solid > logs/log.checkMesh.solid 2>&1

decomposePar -allRegions -force \
    > "logs/decomposePar-${SLURM_JOB_ID}.log" 2>&1

mpirun -np "${SLURM_NTASKS}" chtMultiRegionFoam -parallel \
    > logs/log.chtMultiRegionFoam 2>&1
