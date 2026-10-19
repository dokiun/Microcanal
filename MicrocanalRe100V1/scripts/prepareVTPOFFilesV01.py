#!/usr/bin/env python3
###!/usr/bin/env /usr/local/anaconda3/bin/python3
###!/usr/bin/env /usr/local/bin/python3
#
#Import modules
import os
import re
import sys
import shutil
import numpy as np
from argparse import ArgumentParser

def main():
    """
This script requires one mandatory argument:
Argument must be the name of the VTP filename to be postprocessed.
Please, adjust and run again.

Written by C.Duque
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR 
PURPOSE AND NONINFRINGEMENT.
    """

    parser = ArgumentParser(
            description='''
            Adjust VTP files with data from OpenFOAM simulations for sequential paraView visualization
            ''')
    parser.add_argument("-f", "--file", dest='vtpDataFile', default="file.vtp", 
                        action='store', type=str,
                        help="VTP data filename to be looked up: VTPFILE", metavar="VTPFILE")
    parser.add_argument("-d", "--directory", dest='targetDir', default="./", 
                        action='store', type=str,
                        help="Read VTP files from time dirs in TARGETDIR", metavar="TARGETDIR")
    parser.add_argument("-c", "--correct", dest='correctForParaview', action='store_true',
                        help="Correct keyword float in VTPFILE for use in ParaView 5.9+")

    if len(sys.argv) < 2:
        print("Not enough arguments... ")
        print(main.__doc__)
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    
    # Lectura de datos entrada
    correctVtpFile = args.correctForParaview
    vtpDataFile = args.vtpDataFile
    vtpDataFileName = os.path.basename(vtpDataFile+".vtp")
    rootdir = args.targetDir
    storeDir = os.path.join(rootdir,"orderedVTPFiles")
    if (not os.path.exists(storeDir)):
        os.mkdir(storeDir)
    print("Testing ",vtpDataFile)
    print("Reading VTP files stored in time dirs within ",rootdir)
    print("Storing ordered VTP files in ",storeDir)
    zeroTime = np.float128(0.0);
    expression1= re.compile("^[0-9].[0-9]");
    expression2= re.compile("^[0-9]");
    getHeader = True
    fileCounter = 0;
    
    dirsList = next(os.walk(rootdir))[1]
    orderedDirs = np.array([],dtype=np.float128);
    for dir in dirsList:
        try:
            numericDir = np.float128(dir)
            orderedDirs= np.append(np.array([numericDir],dtype=np.float128),orderedDirs)
        except ValueError:
            pass
    orderedDirs.sort()
    
    dirsList = [];
    for dir in orderedDirs:
        if dir.is_integer():
            dirsList.append(str(int(dir)))
        else:
            dirsList.append(str(dir))
    
    for subdir in dirsList:
        file2move = os.path.join(rootdir,subdir,vtpDataFileName);
        #print("file2Move: ",file2move)
        #print("os.path.exists(file2move):",os.path.exists(file2move))
        #print("expression1.match(subdir)",expression1.match(subdir))
        #print("expression2.match(subdir)",expression2.match(subdir))
        if (
                (os.path.exists(file2move) and expression1.match(subdir)) or
                (os.path.exists(file2move) and expression2.match(subdir))
        ):
            newVtpFileName = \
                    os.path.join(storeDir,vtpDataFile + "_{0:0>4d}".format(fileCounter)+".vtp")
            print (file2move, " exists, and it will be moved to ", newVtpFileName)
            shutil.copy2(file2move,newVtpFileName)
            fileCounter+=1;
            if (correctVtpFile):
                command = ("sed -i '' -e 's/float/double/' " + newVtpFileName);
                os.system(command);
    
    print("\n Postprocessing VTP files finished")

# -----------------------------------------------------------------
# Main function call
if __name__ == "__main__":
    main()
# -----------------------------------------------------------------

# End of main function call
        
