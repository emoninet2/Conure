import os
import subprocess
import copy
import itertools
import shutil
import json
import logging
import emxConfig  # assuming this module is available


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[94m",     # Blue
        logging.INFO: "\033[92m",      # Green
        logging.WARNING: "\033[93m",   # Yellow
        logging.ERROR: "\033[91m",     # Red
        logging.CRITICAL: "\033[95m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        timestamp = self.formatTime(record, self.datefmt)
        msg = super().format(record)
        return f"{timestamp} [EMX] {color}{msg}{self.RESET}"



# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter('%(levelname)s - %(message)s'))
    logger.addHandler(handler)


def configure_logger(level: str = "info", use_color: bool = True):
    """
    Configure the logger level and formatting.
    """
    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    logger.setLevel(log_levels.get(level.lower(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = ColorFormatter('%(asctime)s - %(levelname)s - %(message)s') if use_color else \
                    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

import os
import subprocess
import logging
import uuid

logger = logging.getLogger(__name__)



def emx(emxArgs):
    """
    Uploads the GDS file to a unique remote temp dir, runs 'emx',
    fetches the S‑ and Y‑parameter files, then (optionally) cleans up.
    """

    logging.critical("WOW")

    # -------------------------------------------------------------------
    # Hard‑coded SSH settings
    ssh_jump = "habiburr@login.uio.no"
    ssh_host = "habiburr@nano.ifi.uio.no"
    # generate a unique temp directory on the remote
    remote_temp_dir = f"/tmp/emx_{uuid.uuid4().hex[:8]}"
    # -------------------------------------------------------------------

    # 0) ensure local output
    os.makedirs(emxArgs["outputPath"], exist_ok=True)

    # 1) make the remote temp dir
    subprocess.run([
        "ssh", "-o", f"ProxyJump={ssh_jump}", ssh_host,
        f"mkdir -p {remote_temp_dir}"
    ], check=True)

    # 2) upload the GDS
    local_gds   = emxArgs["gdsFile"]
    gds_name    = os.path.basename(local_gds)
    remote_gds  = f"{ssh_host}:{remote_temp_dir}/{gds_name}"
    subprocess.run([
        "scp", "-o", f"ProxyJump={ssh_jump}",
        local_gds, remote_gds
    ], check=True)
    logger.info(f"Uploaded {gds_name} to {remote_temp_dir}")

    # 3) build the remote 'emx' command
    cmd = [
        "emx",
        os.path.join(remote_temp_dir, gds_name),
        emxArgs["gdsCellName"],
        emxArgs["emxProcPath"]
    ]

    # — repeat all your flag logic from before…
    if "edgeWidth" in emxArgs:
        cmd += ["-e", str(emxArgs["edgeWidth"])]
    if emxArgs.get("3dCond") and emxArgs.get("edgeWidth") is True:
        cmd.append("--3d=*")
    if "thickness" in emxArgs:
        cmd += ["-t", str(emxArgs["thickness"])]
    if "viaSeparation" in emxArgs:
        cmd += ["-v", str(emxArgs["viaSeparation"])]

    port_count = 0
    for port in emxArgs["simulatingPorts"]:
        pid = port["id"]
        if port["type"].lower() == "differential":
            plus  = emxArgs["designPorts"]["data"][port["plus"]]["label"]
            minus = emxArgs["designPorts"]["data"][port["minus"]]["label"]
            cmd.append(f"-p P{pid:03d}={plus}:{minus}")
        else:
            plus = emxArgs["designPorts"]["data"][port["plus"]]["label"]
            cmd.append(f"-p P{pid:03d}={plus}")
    for port in emxArgs["simulatingPorts"]:
        pid = port["id"]
        if port["enable"]:
            cmd.append(f"-i P{pid:03d}")
            port_count += 1
        else:
            cmd.append(f"-x P{pid:03d}")

    if "sweepFreq" not in emxArgs:
        raise ValueError("Sweep frequencies not defined")
    sf = emxArgs["sweepFreq"]
    cmd += ["--sweep", str(sf["startFreq"]), str(sf["stopFreq"])]
    if sf.get("useStepSize"):
        cmd += ["--sweep-stepsize", str(sf["stepSize"])]
    else:
        cmd += ["--sweep-num-steps", str(sf["stepNum"])]

    for key, flag in [
        ("referenceImpedance", "--s-impedance"),
        ("verbose",              "--verbose"),
        ("parallelCPU",          "--parallel"),
        ("simultaneousFrequencies","--simultaneous-frequencies")
    ]:
        if key in emxArgs:
            cmd.append(f"{flag}={emxArgs[key]}")
    if emxArgs.get("printCommandLine"):
        cmd.append("--print-command-line")
    if emxArgs.get("dumpConnectivity"):
        cmd.append("--dump-connectivity")
    if emxArgs.get("quasistatic"):
        cmd.append("--quasistatic")
    if emxArgs.get("recommendedMemory"):
        cmd.append("--recommended-memory")
    if "labelDepth" in emxArgs:
        cmd += ["-l", str(emxArgs["labelDepth"])]

    # tell emx to write into our remote_temp_dir
    output_name = emxArgs.get("outputName", emxArgs["gdsCellName"])
    for fmt, use in emxArgs["SParam"]["formats"].items():
        if fmt.lower() == "touchstone" and use:
            cmd += [
                "--format", "touchstone", "-s",
                os.path.join(remote_temp_dir, f"{output_name}.s{port_count}p")
            ]
    for fmt, use in emxArgs["YParam"]["formats"].items():
        if fmt.lower() == "touchstone" and use:
            cmd += [
                "--format", "touchstone", "-y",
                os.path.join(remote_temp_dir, f"{output_name}.y{port_count}p")
            ]

    # 4) run remotely
    subprocess.run([
        "ssh", "-o", f"ProxyJump={ssh_jump}", ssh_host,
        " ".join(cmd)
    ], check=True)
    logger.info("Remote emx done")

    # 5) fetch results back
    results = {}
    for ext in ("s", "y"):
        fname = f"{output_name}.{ext}{port_count}p"
        subprocess.run([
            "scp", "-o", f"ProxyJump={ssh_jump}",
            f"{ssh_host}:{remote_temp_dir}/{fname}",
            os.path.join(emxArgs["outputPath"], fname)
        ], check=True)
        results[f"{ext}Params"] = os.path.join(emxArgs["outputPath"], fname)
        logger.info(f"Fetched {fname}")

    # 6) (optional) clean up the remote temp dir
    subprocess.run([
        "ssh", "-o", f"ProxyJump={ssh_jump}", ssh_host,
        f"rm -rf {remote_temp_dir}"
    ], check=True)

    return results



def emx2(emxArgs):
    """
    Constructs and executes the simulation command based on the provided arguments.
    Raises a ValueError if mandatory keys (e.g. sweep frequencies) are missing.
    """

    # Dynamically set log level (default: "info")
    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
        "none": logging.CRITICAL + 10  # Effectively disables all logging
    }   
    log_level_str = emxArgs.get("logLevel", "info").lower()
    log_level = log_levels.get(log_level_str, logging.INFO)
    logger.setLevel(log_level)

    # Ensure logger handler is attached
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(ColorFormatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

    # Optional: run any environment setup commands.
    # env_command = 'source /projects/bitstream/emon/projects/conure/simulator/TSMC65nmRF_session_IC618'
    # process = subprocess.Popen(env_command, shell=True, executable='/bin/bash')
    # process.communicate()


    # Build command parts as a list for clarity and easy joining
    command_parts = [
        emxArgs["emxPath"],
        emxArgs["gdsFile"],
        emxArgs["gdsCellName"],
        emxArgs["emxProcPath"]
    ]

    # Add optional flags
    if "edgeWidth" in emxArgs:
        command_parts.extend(["-e", str(emxArgs["edgeWidth"])])

    if "3dCond" in emxArgs and emxArgs.get("edgeWidth") == True:
        command_parts.append("--3d=*")

    if "thickness" in emxArgs:
        command_parts.extend(["-t", str(emxArgs["thickness"])])

    if "viaSeparation" in emxArgs:
        command_parts.extend(["-v", str(emxArgs["viaSeparation"])])

    # Create port definitions
    for simPort in emxArgs["simulatingPorts"]:
        emxPortId = simPort["id"]
        if simPort["type"].lower() == "differential":
            plusPort = simPort["plus"]
            minusPort = simPort["minus"]
            plusPortLabel = emxArgs["designPorts"]["data"][plusPort]["label"]
            minusPortLabel = emxArgs["designPorts"]["data"][minusPort]["label"]
            command_parts.append(f"-p P{emxPortId:03d}={plusPortLabel}:{minusPortLabel}")
        elif simPort["type"].lower() == "single":
            plusPort = simPort["plus"]
            plusPortLabel = emxArgs["designPorts"]["data"][plusPort]["label"]
            command_parts.append(f"-p P{emxPortId:03d}={plusPortLabel}")

    # Enable or disable the ports
    PortCount = 0
    for simPort in emxArgs["simulatingPorts"]:
        emxPortId = simPort["id"]
        if simPort["enable"]:
            command_parts.append(f"-i P{emxPortId:03d}")
            PortCount += 1
        else:
            command_parts.append(f"-x P{emxPortId:03d}")

    # Configure the frequency sweep
    if "sweepFreq" in emxArgs:
        startFreq = emxArgs["sweepFreq"]["startFreq"]
        stopFreq = emxArgs["sweepFreq"]["stopFreq"]
        command_parts.extend(["--sweep", str(startFreq), str(stopFreq)])
        if emxArgs["sweepFreq"].get("useStepSize", False):
            stepSize = emxArgs["sweepFreq"]["stepSize"]
            command_parts.extend(["--sweep-stepsize", str(stepSize)])
        else:
            stepNum = emxArgs["sweepFreq"]["stepNum"]
            command_parts.extend(["--sweep-num-steps", str(stepNum)])
    else:
        logger.error("Sweep frequencies not defined")
        raise ValueError("Sweep frequencies not defined")

    if "referenceImpedance" in emxArgs:
        command_parts.append(f"--s-impedance={emxArgs['referenceImpedance']}")

    if "verbose" in emxArgs:
        command_parts.append(f"--verbose={emxArgs['verbose']}")

    if emxArgs.get("printCommandLine") is True:
        command_parts.append("--print-command-line")

    if "labelDepth" in emxArgs:
        command_parts.extend(["-l", str(emxArgs["labelDepth"])])

    if emxArgs.get("dumpConnectivity") is True:
        command_parts.append("--dump-connectivity")

    if emxArgs.get("quasistatic") is True:
        command_parts.append("--quasistatic")

    if "parallelCPU" in emxArgs:
        command_parts.append(f"--parallel={emxArgs['parallelCPU']}")

    if "simultaneousFrequencies" in emxArgs:
        command_parts.append(f"--simultaneous-frequencies={emxArgs['simultaneousFrequencies']}")

    if emxArgs.get("recommendedMemory") is True:
        command_parts.append("--recommended-memory")

    outputName = emxArgs.get("outputName") or emxArgs.get("gdsCellName")

    # Writing S-Parameters
    for outFormat, useFormat in emxArgs["SParam"]["formats"].items():
        if outFormat.lower() == "touchstone" and useFormat:
            command_parts.extend([
                "--format", "touchstone", "-s",
                os.path.join(emxArgs["outputPath"], f"{outputName}.s{PortCount}p")
            ])

    # Writing Y-Parameters
    for outFormat, useFormat in emxArgs["YParam"]["formats"].items():
        if outFormat.lower() == "touchstone" and useFormat:
            command_parts.extend([
                "--format", "touchstone", "-y",
                os.path.join(emxArgs["outputPath"], f"{outputName}.y{PortCount}p")
            ])

    # Ensure output path exists
    os.makedirs(emxArgs["outputPath"], exist_ok=True)

    # Join command parts into a full command string
    full_command = " ".join(command_parts)
    logger.debug(f"Executing command: {full_command}")

    # Save the command to run the simulation
    # command_script_path = os.path.join(emxArgs["outputPath"], "emx_command.sh")
    # with open(command_script_path, "w") as f:
    #     f.write("#!/bin/bash\n")
    #     f.write(full_command + "\n")
    # os.chmod(command_script_path, 0o755)

    
    try:
        # subprocess.run(full_command, shell=True, check=True)
        # import subprocess

        if log_level_str == "none":
            subprocess.run(full_command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            result = subprocess.run(
                full_command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True  # ensures output is str, not bytes
            )

            if result.stdout:
                logger.info(result.stdout.strip())

            if result.stderr:
                logger.error(result.stderr.strip())

        logger.info("Command executed successfully.")
    except subprocess.CalledProcessError as error:
        #logger.error(f"Command failed with error: {error}")
        raise


def simulate(gdsFilePath, artworkData, emxConfig, outputDir, outputName):
    """
    Updates the configuration with artwork and output info, then runs the simulation.
    """
    emxConfigX = copy.deepcopy(emxConfig)
    emxConfigX["gdsFile"] = gdsFilePath
    emxConfigX["outputPath"] = outputDir  #Maybe not necessary. 
    emxConfigX["outputName"] = outputName

    logger.info(f"Artwork parameters: {artworkData.get('parameters')}")
    emxConfigX["gdsCellName"] = artworkData["metadata"]["name"]
    emxConfigX["ports"] = artworkData["ports"]
    emxConfigX["designPorts"] = artworkData["ports"]
    emxConfigX["simulatingPorts"] = artworkData["ports"]["config"]["simulatingPorts"]

    try:
        emx(emxConfigX)
    except Exception as error:
        logger.error(f"Simulation failed")
        raise


def simulateSweep(InductorData, emxConfig, sweepParam, outputDir):
    """
    Iterates over parameter sweeps, updates the design for each permutation, writes the parameter file, and runs simulation.
    Returns a two-element list: [TotalRuns, successfulRuns].
    """
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
        run_output_dir = os.path.join(outputDir, f"RunID_{RunID:04d}")
        InductorDataX["parameters"]["outputDir"] = run_output_dir
        InductorDataX["parameters"]["name"] += f"_RunID_{RunID:04d}"

        logger.info(f"{InductorData['parameters']['name']} | RUN ID: {RunID} | Permutation: {permutation}")

        param_file_path = os.path.join(run_output_dir, "parameters.json")
        if os.path.exists(param_file_path):
            RunID += 1
            continue
        else:
            runData = {"runID": None, "parameters": {}}
            TotalRuns = len(permutation)
            for i in range(TotalRuns):
                InductorDataX["parameters"][sweepPar[i]] = permutation[i]
                runData["parameters"][sweepPar[i]] = permutation[i]

            runData["parameters"]["rings"] = InductorDataX["parameters"]["rings"]
            runDataJSON = json.dumps(runData)
            os.makedirs(run_output_dir, exist_ok=True)

            with open(param_file_path, "w") as parfile:
                parfile.write(runDataJSON)

            RunID += 1

            # The following functions (Inductor and simulate) are assumed to be defined elsewhere.
            portCount = len(InductorDataX["ports"]["config"]["simulatingPorts"])
            gdsPath = os.path.join(run_output_dir, f"{InductorDataX['parameters']['name']}.gds")
            sParamPath = os.path.join(run_output_dir, f"{InductorDataX['parameters']['name']}.s{portCount}p")

            if not os.path.exists(gdsPath):
                try:
                    pass
                except Exception as error:
                    logger.error(f"Inductor generation failed for RunID {RunID - 1}: {error}")
                    continue

            if os.path.exists(sParamPath):
                successfulRuns += 1
            else:
                try:
                    simulate(
                        os.path.join(run_output_dir, f"{InductorDataX['parameters']['name']}.gds"),
                        InductorDataX,
                        emxConfig
                    )
                    successfulRuns += 1
                except Exception as error:
                    logger.error(f"Simulation failed for RunID {RunID - 1}: {error}")

    TotalRuns = RunID
    return [TotalRuns, successfulRuns]








# import os
# import subprocess
# import copy
# import emxConfig
# import itertools
# import copy
# import shutil
# import json

# def emx(emxArgs):

#     command = emxArgs["emxPath"] + " "
#     command += emxArgs["gdsFile"] + " "
#     command += emxArgs["gdsCellName"] + " "
#     command += emxArgs["emxProcPath"] + " "

#     if "edgeWidth" in emxArgs:
#         command += "-e " + str(emxArgs["edgeWidth"]) + " "

#     if "3dCond" in emxArgs and emxArgs["edgeWidth"] == True:
#         command += "--3d=* "

#     if "thickness" in emxArgs:
#         command += "-t " + str(emxArgs["thickness"]) + " "

#     if "viaSeparation" in emxArgs:
#         command += "-v " + str(emxArgs["viaSeparation"]) + " "



#     # creating the ports
#     for simulatingPorts in emxArgs["simulatingPorts"]:
#         if simulatingPorts["type"].lower() == "differential":
#             plusPort = simulatingPorts["plus"]
#             minusPort = simulatingPorts["minus"]
#             plusPortLabel = emxArgs["designPorts"]["data"][plusPort]["label"]
#             minusPortLabel = emxArgs["designPorts"]["data"][minusPort]["label"]
#             emxPortId = simulatingPorts["id"]
#             command += "-p P" + "{:03d}".format(emxPortId) + "=" + plusPortLabel + ":" + minusPortLabel+ " "
#             pass
#         elif simulatingPorts["type"].lower() == "single":
#             plusPort = simulatingPorts["plus"]
#             plusPortLabel = emxArgs["designPorts"]["data"][plusPort]["label"]
#             emxPortId = simulatingPorts["id"]
#             command += "-p P" + "{:03d}".format(emxPortId) + "=" + plusPortLabel + " "
#             pass


#     #enabling Ports
#     PortCount = 0
#     for simulatingPorts in emxArgs["simulatingPorts"]:
#        emxPortId = simulatingPorts["id"]
#        if simulatingPorts["enable"]:
#            command += "-i P" + "{:03d}".format(emxPortId) + " "
#            PortCount+= 1
#        else:
#            command += "-x P" + "{:03d}".format(emxPortId) + " "


#     # modes of the ports (--mode=)



#     # configuring the sweep
#     if "sweepFreq" in emxArgs:
#         startFreq = emxArgs["sweepFreq"]["startFreq"]
#         stopFreq = emxArgs["sweepFreq"]["stopFreq"]
#         command += "--sweep " + str(startFreq) + " " + str(stopFreq) + " "
#         if emxArgs["sweepFreq"]["useStepSize"] == True:
#             stepSize = emxArgs["sweepFreq"]["stepSize"]
#             command += "--sweep-stepsize " + str(stepSize) + " "
#         else:
#             stepNum = emxArgs["sweepFreq"]["stepNum"]
#             command += "--sweep-num-steps  " + str(stepNum) + " "
#     else:
#         exit("sweep frequencies not defined")

#     if "referenceImpedance" in emxArgs:
#         command += "--s-impedance=" + str(emxArgs["referenceImpedance"]) + " "

#     if "verbose" in emxArgs:
#         command += "--verbose=" + str(emxArgs["verbose"]) + " "

#     if "printCommandLine" in emxArgs and emxArgs["printCommandLine"] == True:
#         command += "--print-command-line "

#     if "labelDepth" in emxArgs:
#         command += "-l " + str(emxArgs["labelDepth"]) + " "

#     if "dumpConnectivity" in emxArgs and emxArgs["dumpConnectivity"] == True:
#         command += "--dump-connectivity "

#     if "quasistatic" in emxArgs and emxArgs["quasistatic"] == True:
#         command += "--quasistatic "

#     if "parallelCPU" in emxArgs:
#         command += "--parallel=" + str(emxArgs["parallelCPU"]) + " "

#     if "simultaneousFrequencies" in emxArgs:
#         command += "--simultaneous-frequencies=" + str(emxArgs["simultaneousFrequencies"]) + " "

#     if "recommendedMemory" in emxArgs and emxArgs["recommendedMemory"] == True:
#         command += "--recommended-memory "


#     outputName = emxArgs["outputName"]
#     if outputName == None:
#         outputName = emxArgs["gdsCellName"] 

#     # writing S-Parameters
#     for outFormat, useFormat in emxArgs["SParam"]["formats"].items():
#         if outFormat == "touchstone" and useFormat == True:
#             command += "--format touchstone -s " + emxArgs["outputPath"] + "/" + outputName + ".s" + str(
#                 PortCount) + "p "

#     # writing Y-Parameters
#     for outFormat, useFormat in emxArgs["YParam"]["formats"].items():
#         if outFormat == "touchstone" and useFormat == True:
#             command += "--format touchstone -s " + emxArgs["outputPath"] + "/" +outputName + ".y" + str(
#                 PortCount) + "p "


#     if not os.path.exists(emxArgs["outputPath"]):
#         os.makedirs(emxArgs["outputPath"] )

#     #print(command)
    
#     os.system(command)



# def simulate(gdsFilePath, artworkData, emxConfig, outputDir, outputName):


#     #emxConfigX = copy.deepcopy(emxConfig.emxConfig)

    
#     InductorData = artworkData
#     #InductorData["parameters"]["name"] = outputName
#     emxConfigX = emxConfig

#     emxConfigX["gdsFile"] = gdsFilePath
#     #emxConfigX["gdsFile"] = InductorDataJSON["parameters"]["outputDir"] + "/" + InductorDataJSON["parameters"]["name"] + ".gds"
#     emxConfigX["outputPath"] = outputDir
#     emxConfigX["outputName"] = outputName

    
#     print(artworkData["parameters"])


#     emxConfigX["gdsCellName"] = InductorData["metadata"]["name"]
#     emxConfigX["ports"] = InductorData["ports"]

#     emxConfigX["designPorts"] = InductorData["ports"]
#     emxConfigX["simulatingPorts"] = InductorData["ports"]["config"]["simulatingPorts"]

#     emx(emxConfigX)
    
    


# def simulateSweep(InductorData, emxConfig, sweepParam, outputDir):
    

#     sweepPar = []
#     sweepData = []
#     for param, paramSweepData in sweepParam["parameters"].items():
#         sweepPar.append(param)
#         sweepData.append(paramSweepData)

#     permutations = itertools.product(*sweepData)

#     RunID = 0
#     successfulRuns = 0
#     for permutation in permutations:
        

#         InductorDataX = copy.deepcopy(InductorData)
#         InductorDataX["parameters"]["outputDir"] = outputDir+  "/RunID_" + "{:04d}".format(RunID)
#         #InductorDataX["parameters"]["outputDir"] +=  "/RunID_" + "{:04d}".format(RunID)
#         InductorDataX["parameters"]["name"] +=  "_RunID_" + "{:04d}".format(RunID)


#         print(InductorData["parameters"]["name"] + "\r\nRUN ID: " + str(RunID) + "\r\n" + str(permutation))

#         if os.path.exists(InductorDataX["parameters"]["outputDir"] + "/parameters.json"):
#             RunID += 1
#         else:

#             runData = {
#                 "runID" : None,
#                 "parameters" : {},
#             }

#             TotalRuns = len(permutation)

#             for i in range(TotalRuns):
#                 InductorDataX["parameters"][sweepPar[i]] = permutation[i]
#                 runData["parameters"][sweepPar[i]] = permutation[i] #used to just write as a text file of the parameter value

#             runData["parameters"]["rings"] = InductorDataX["parameters"]["rings"]
#             runDataJSON = json.dumps(runData)


#             if not os.path.exists(InductorDataX["parameters"]["outputDir"]):
#                 os.makedirs(InductorDataX["parameters"]["outputDir"])

#             with open(InductorDataX["parameters"]["outputDir"] + "/parameters.json", "w") as parfile:
#                 parfile.write(runDataJSON)


#             RunID += 1

#             #Inductor(InductorDataX)
#             #simulate(InductorDataX, emxConfig)

#             #checking if SParam files are generated for the current run
#         portCount = len(InductorDataX["ports"]["config"]["simulatingPorts"])
#         gdsPath = InductorDataX["parameters"]["outputDir"] + "/" + InductorDataX["parameters"]["name"] + ".gds"
#         sParamPath = InductorDataX["parameters"]["outputDir"] + "/" + InductorDataX["parameters"]["name"] + ".s" + str(portCount) +"p"


#         if os.path.exists( gdsPath):
#             pass
#             #successfulRuns += 1
#         else:
#             Inductor(InductorDataX)

#         if os.path.exists( sParamPath):
#             successfulRuns += 1
#         else:
#             simulate(InductorDataX, emxConfig)

        
#     TotalRuns = RunID
#     return [TotalRuns , successfulRuns]
