#!/bin/bash -l
# -------------------------
#SBATCH --ntasks 1
#SBATCH --mem 4G
#SBATCH --time 1:00:00
#SBATCH --mail-type ALL
#SBATCH --job-name=postProcessingChannel3Dv14
#SBATCH --output=P-%x.%j.out
#SBATCH --error=P-%x.%j.err
#SBATCH --account=alberinf-operating-theatre-fluid-flow
#SBATCH --qos bbdefault # castles # bbshort # 
# -------------------------
#set -e

module purge; module load bluebear
module load bear-apps/2023a/live
module load OpenFOAM/v2406-foss-2023a
source $FOAM_BASH
source $WM_PROJECT_DIR/bin/tools/RunFunctions

timesToProcess='18:20'

#runApplication reconstructPar -latestTime
#runApplication -s 1 reconstructPar -newTimes
runApplication -s 1 reconstructPar -allRegions  -newTimes
#runApplication -s 1 reconstructPar -time ${timesToProcess}

sleep 5

mv log.reconstructPar.1  "reconstructPar-$(date +"%Y_%m_%d_%I_%M_%p")-V01.log"

#sleep 5
#
#runApplication foamToVTK -no-boundary -no-internal -time ${timesToProcess}
#
#sleep 5
#
#mv log.foamToVTK  "foamToVTK-$(date +"%Y_%m_%d_%I_%M_%p").log"
#

exit 0
