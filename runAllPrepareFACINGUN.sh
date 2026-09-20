#!/bin/bash
# -------------------------
#SBATCH --ntasks 1
#SBATCH --mem 8G
#SBATCH --time 48:00:00
#SBATCH --mail-type ALL
#SBATCH --job-name=preProcessingChannel3Dv14
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --account=alberinf-operating-theatre-fluid-flow
#SBATCH --partition=bbshort #  bbdefault # castles # # hpc-short # 
# -------------------------
#set -e

module load openfoam/2412
source $FOAM_INST_DIR/openfoam2412/etc/bashrc
source $WM_PROJECT_DIR/bin/tools/RunFunctions

#cleanCase
rm -rf 0
cp -r 0-orig-asp 0
rm -rf constant/fluid/polyMesh
rm -rf constant/solid/polyMesh
#
## Get application name
##application=$(getApplication)
#
### Etapa 1
cp system/fluid/blockMeshDict system/blockMeshDict
runApplication -s fluid blockMesh &&
  mv log.blockMesh.fluid "blockMeshFluid-$(date +"%Y_%m_%d_%I_%M_%p").log"
mv constant/polyMesh constant/fluid/
##
#### Etapa 2
cp system/solid/blockMeshDict system/blockMeshDict
runApplication -s solid blockMesh &&
  mv log.blockMesh.solid "blockMeshSolid-$(date +"%Y_%m_%d_%I_%M_%p").log"
mv constant/polyMesh constant/solid/
##
#### Etapa 3
runApplication -s solid changeDictionary -region solid -subDict dictionaryReplacement &&
  mv log.changeDictionary.solid "changeDictionarySolid-$(date +"%Y_%m_%d_%I_%M_%p").log"
runApplication -s fluid changeDictionary -region fluid -subDict dictionaryReplacement &&
  mv log.changeDictionary.fluid "changeDictionaryFluid-$(date +"%Y_%m_%d_%I_%M_%p").log"
##
#### Etapa 4
##runApplication initAlphaField -region fluid &&
##  mv log.initAlphaField "initAlphaField-$(date +"%Y_%m_%d_%I_%M_%p").log"
runApplication -s fluid setFields -region fluid &&
  mv log.setFields.fluid "setFieldsFluid-$(date +"%Y_%m_%d_%I_%M_%p").log"
runApplication -s solid setFields -region solid &&
  mv log.setFields.solid "setFieldsSolid-$(date +"%Y_%m_%d_%I_%M_%p").log"
##
#### Etapa 5
runApplication -s solid renumberMesh -region solid -overwrite &&
  mv log.renumberMesh.solid "renumberMeshSolid-$(date +"%Y_%m_%d_%I_%M_%p").log"
##
runApplication -s fluid renumberMesh -region fluid -overwrite &&
  mv log.renumberMesh.fluid "renumberMeshFluid-$(date +"%Y_%m_%d_%I_%M_%p").log"
#
#### Etapa 6
runApplication -s 1 checkMesh -allRegions  -allTopology  &&
    mv log.checkMesh.1 "checkMesh-$(date +"%Y_%m_%d_%I_%M_%p").log"

## Etapa 7
runApplication decomposePar -allRegions -latestTime && 
    mv log.decomposePar "decomposePar-$(date +"%Y_%m_%d_%I_%M_%p").log"

exit 0
