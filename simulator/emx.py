import os
import subprocess
import copy
import emxConfig
import itertools
import copy
import shutil
import json

def emx(emxArgs):

    command = emxArgs["emxPath"] + " "
    command += emxArgs["gdsFile"] + " "
    command += emxArgs["gdsCellName"] + " "
    command += emxArgs["emxProcPath"] + " "

    if "edgeWidth" in emxArgs:
        command += "-e " + str(emxArgs["edgeWidth"]) + " "

    if "3dCond" in emxArgs and emxArgs["edgeWidth"] == True:
        command += "--3d=* "

    if "thickness" in emxArgs:
        command += "-t " + str(emxArgs["thickness"]) + " "

    if "viaSeparation" in emxArgs:
        command += "-v " + str(emxArgs["viaSeparation"]) + " "



    # creating the ports
    for simulatingPorts in emxArgs["simulatingPorts"]:
        if simulatingPorts["type"].lower() == "differential":
            plusPort = simulatingPorts["plus"]
            minusPort = simulatingPorts["minus"]
            plusPortLabel = emxArgs["designPorts"]["data"][plusPort]["label"]
            minusPortLabel = emxArgs["designPorts"]["data"][minusPort]["label"]
            emxPortId = simulatingPorts["id"]
            command += "-p P" + "{:03d}".format(emxPortId) + "=" + plusPortLabel + ":" + minusPortLabel+ " "
            pass
        elif simulatingPorts["type"].lower() == "single":
            plusPort = simulatingPorts["plus"]
            plusPortLabel = emxArgs["designPorts"]["data"][plusPort]["label"]
            emxPortId = simulatingPorts["id"]
            command += "-p P" + "{:03d}".format(emxPortId) + "=" + plusPortLabel + " "
            pass


    #enabling Ports
    PortCount = 0
    for simulatingPorts in emxArgs["simulatingPorts"]:
       emxPortId = simulatingPorts["id"]
       if simulatingPorts["enable"]:
           command += "-i P" + "{:03d}".format(emxPortId) + " "
           PortCount+= 1
       else:
           command += "-x P" + "{:03d}".format(emxPortId) + " "


    # modes of the ports (--mode=)



    # configuring the sweep
    if "sweepFreq" in emxArgs:
        startFreq = emxArgs["sweepFreq"]["startFreq"]
        stopFreq = emxArgs["sweepFreq"]["stopFreq"]
        command += "--sweep " + str(startFreq) + " " + str(stopFreq) + " "
        if emxArgs["sweepFreq"]["useStepSize"] == True:
            stepSize = emxArgs["sweepFreq"]["stepSize"]
            command += "--sweep-stepsize " + str(stepSize) + " "
        else:
            stepNum = emxArgs["sweepFreq"]["stepNum"]
            command += "--sweep-num-steps  " + str(stepNum) + " "
    else:
        exit("sweep frequencies not defined")

    if "referenceImpedance" in emxArgs:
        command += "--s-impedance=" + str(emxArgs["referenceImpedance"]) + " "

    if "verbose" in emxArgs:
        command += "--verbose=" + str(emxArgs["verbose"]) + " "

    if "printCommandLine" in emxArgs and emxArgs["printCommandLine"] == True:
        command += "--print-command-line "

    if "labelDepth" in emxArgs:
        command += "-l " + str(emxArgs["labelDepth"]) + " "

    if "dumpConnectivity" in emxArgs and emxArgs["dumpConnectivity"] == True:
        command += "--dump-connectivity "

    if "quasistatic" in emxArgs and emxArgs["quasistatic"] == True:
        command += "--quasistatic "

    if "parallelCPU" in emxArgs:
        command += "--parallel=" + str(emxArgs["parallelCPU"]) + " "

    if "simultaneousFrequencies" in emxArgs:
        command += "--simultaneous-frequencies=" + str(emxArgs["simultaneousFrequencies"]) + " "

    if "recommendedMemory" in emxArgs and emxArgs["recommendedMemory"] == True:
        command += "--recommended-memory "


    outputName = emxArgs["outputName"]
    if outputName == None:
        outputName = emxArgs["gdsCellName"] 

    # writing S-Parameters
    for outFormat, useFormat in emxArgs["SParam"]["formats"].items():
        if outFormat == "touchstone" and useFormat == True:
            command += "--format touchstone -s " + emxArgs["outputPath"] + "/" + outputName + ".s" + str(
                PortCount) + "p "

    # writing Y-Parameters
    for outFormat, useFormat in emxArgs["YParam"]["formats"].items():
        if outFormat == "touchstone" and useFormat == True:
            command += "--format touchstone -s " + emxArgs["outputPath"] + "/" +outputName + ".y" + str(
                PortCount) + "p "


    if not os.path.exists(emxArgs["outputPath"]):
        os.makedirs(emxArgs["outputPath"] )

    #print(command)
    
    os.system(command)



def simulate(gdsFilePath, artworkData, emxConfig, outputDir, outputName):


    #emxConfigX = copy.deepcopy(emxConfig.emxConfig)

    
    InductorData = artworkData
    #InductorData["parameters"]["name"] = outputName
    emxConfigX = emxConfig

    emxConfigX["gdsFile"] = gdsFilePath
    #emxConfigX["gdsFile"] = InductorDataJSON["parameters"]["outputDir"] + "/" + InductorDataJSON["parameters"]["name"] + ".gds"
    emxConfigX["outputPath"] = outputDir
    emxConfigX["outputName"] = outputName

    
    print(artworkData["parameters"])


    emxConfigX["gdsCellName"] = InductorData["metadata"]["name"]
    emxConfigX["ports"] = InductorData["ports"]

    emxConfigX["designPorts"] = InductorData["ports"]
    emxConfigX["simulatingPorts"] = InductorData["ports"]["config"]["simulatingPorts"]

    emx(emxConfigX)
    
    


def simulateSweep(InductorData, emxConfig, sweepParam, outputDir):
    

    sweepPar = []
    sweepData = []
    for param, paramSweepData in sweepParam["parameters"].items():
        sweepPar.append(param)
        sweepData.append(paramSweepData)

    permutations = itertools.product(*sweepData)

    RunID = 0
    successfulRuns = 0
    for permutation in permutations:
        

        InductorDataX = copy.deepcopy(InductorData)
        InductorDataX["parameters"]["outputDir"] = outputDir+  "/RunID_" + "{:04d}".format(RunID)
        #InductorDataX["parameters"]["outputDir"] +=  "/RunID_" + "{:04d}".format(RunID)
        InductorDataX["parameters"]["name"] +=  "_RunID_" + "{:04d}".format(RunID)


        print(InductorData["parameters"]["name"] + "\r\nRUN ID: " + str(RunID) + "\r\n" + str(permutation))

        if os.path.exists(InductorDataX["parameters"]["outputDir"] + "/parameters.json"):
            RunID += 1
        else:

            runData = {
                "runID" : None,
                "parameters" : {},
            }

            TotalRuns = len(permutation)

            for i in range(TotalRuns):
                InductorDataX["parameters"][sweepPar[i]] = permutation[i]
                runData["parameters"][sweepPar[i]] = permutation[i] #used to just write as a text file of the parameter value

            runData["parameters"]["rings"] = InductorDataX["parameters"]["rings"]
            runDataJSON = json.dumps(runData)


            if not os.path.exists(InductorDataX["parameters"]["outputDir"]):
                os.makedirs(InductorDataX["parameters"]["outputDir"])

            with open(InductorDataX["parameters"]["outputDir"] + "/parameters.json", "w") as parfile:
                parfile.write(runDataJSON)


            RunID += 1

            #Inductor(InductorDataX)
            #simulate(InductorDataX, emxConfig)

            #checking if SParam files are generated for the current run
        portCount = len(InductorDataX["ports"]["config"]["simulatingPorts"])
        gdsPath = InductorDataX["parameters"]["outputDir"] + "/" + InductorDataX["parameters"]["name"] + ".gds"
        sParamPath = InductorDataX["parameters"]["outputDir"] + "/" + InductorDataX["parameters"]["name"] + ".s" + str(portCount) +"p"


        if os.path.exists( gdsPath):
            pass
            #successfulRuns += 1
        else:
            Inductor(InductorDataX)

        if os.path.exists( sParamPath):
            successfulRuns += 1
        else:
            simulate(InductorDataX, emxConfig)

        
    TotalRuns = RunID
    return [TotalRuns , successfulRuns]
