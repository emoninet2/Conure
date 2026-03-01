import os
import subprocess
import copy
import itertools
import shutil
import json
import logging
#import emxConfig  # assuming this module is available


from common.logger import get_logger
logger = get_logger(__name__, '[EMX]')


import os
import subprocess
import logging
import uuid

logger = logging.getLogger(__name__)


def emx(emxArgs):
    """
    Dispatch to either the local or remote EMX implementation based on:
      emxArgs["remote"]["use"]
    Returns the dict of result paths from the called implementation.
    """
    # Safely pull out the remote config

    remote_cfg = emxArgs.get("remote", {})
    use_remote = bool(remote_cfg.get("use", False))

    # If we're going remote, ensure at least the minimal SSH info is present
    if use_remote:
        # missing = [k for k in ("sshJump", "sshHost") if k not in remote_cfg]
        # if missing:
        #     raise ValueError(f"remote.use is True, but missing config keys: {missing!r}")
        executor = emx_remote
        logger.info("Dispatching EMX to remote execution")
    else:
        executor = emx_local
        logger.info("Dispatching EMX to local execution")

    # Call the selected implementation and return its results
    result = executor(emxArgs)
    logger.debug(f"EMX completed via {'remote' if use_remote else 'local'} path: {result}")
    return result

def emx_remote(emxArgs):
    """
    Uploads the GDS file to a unique remote temp dir, runs 'emx',
    fetches the S- and Y-parameter files, then (optionally) cleans up.
    """
    # -------------------------------------------------------------------
    # 0) Prepare
    # -------------------------------------------------------------------
    logger.debug("Initializing Remote EMX over SSH")
    ssh_host  = emxArgs["remote"]["sshHost"]

    remote_dir = f"/tmp/emx_{uuid.uuid4().hex[:8]}"


    # Ensure local output directory exists
    os.makedirs(emxArgs["outputPath"], exist_ok=True)

    # Build base SSH/SCP commands dynamically
    ssh_base = ["ssh"]
    scp_base = ["scp"]

    # Add ProxyJump if needed
    # if use_proxy and ssh_jump:
    #     ssh_base += ["-o", f"ProxyJump={ssh_jump}"]
    #     scp_base += ["-o", f"ProxyJump={ssh_jump}"]

    # Add identity file if provided
    # if identity_file:
    #     ssh_base += ["-i", identity_file]
    #     scp_base += ["-i", identity_file]

    # Append the target host to SSH command
    ssh_base.append(ssh_host)
    # For SCP, destination/remote path will be appended by the caller

    try:
        # -------------------------------------------------------------------
        # 1) Create remote temp directory
        # -------------------------------------------------------------------
        subprocess.run(ssh_base + [f"mkdir -p {remote_dir}"], check=True)


        # -------------------------------------------------------------------
        # 2) Upload the GDS file
        # -------------------------------------------------------------------
        local_gds = emxArgs["gdsFile"]
        gds_name  = os.path.basename(local_gds)
        remote_gds_dest = f"{ssh_host}:{remote_dir}/{gds_name}"

        subprocess.run(scp_base + [local_gds, remote_gds_dest], check=True)
        logger.info(f"Uploaded {gds_name} → {remote_dir}")

        # -------------------------------------------------------------------
        # 3) Build the EMX command
        # -------------------------------------------------------------------
        cmd = [
            emxArgs["emxPath"],
            os.path.join(remote_dir, gds_name),
            emxArgs["gdsCellName"],
            emxArgs["emxProcPath"],
        ]

        # basic flags
        if "edgeWidth" in emxArgs:
            cmd += ["-e", str(emxArgs["edgeWidth"])]
        if emxArgs.get("3dCond") and "edgeWidth" in emxArgs:
            cmd.append("--3d=*")
        if "thickness" in emxArgs:
            cmd += ["-t", str(emxArgs["thickness"])]
        if "viaSeparation" in emxArgs:
            cmd += ["-v", str(emxArgs["viaSeparation"])]

        # ports: definitions
        port_count = 0
        for port in emxArgs["simulatingPorts"]:
            pid = port["id"]
            plus_label = emxArgs["designPorts"]["data"][port["plus"]]["label"]
            if port["type"].lower() == "differential":
                minus_label = emxArgs["designPorts"]["data"][port["minus"]]["label"]
                cmd.append(f"-p P{pid:03d}={plus_label}:{minus_label}")
            else:
                cmd.append(f"-p P{pid:03d}={plus_label}")

        # ports: enable/disable
        for port in emxArgs["simulatingPorts"]:
            pid = port["id"]
            if port.get("enable", False):
                cmd.append(f"-i P{pid:03d}")
                port_count += 1
            else:
                cmd.append(f"-x P{pid:03d}")

        # sweep settings
        sf = emxArgs.get("sweepFreq")
        if not sf:
            raise ValueError("Sweep frequencies not defined")
        cmd += ["--sweep", str(sf["startFreq"]), str(sf["stopFreq"])]
        if sf.get("useStepSize"):
            cmd += ["--sweep-stepsize", str(sf["stepSize"])]
        else:
            cmd += ["--sweep-num-steps", str(sf["stepNum"])]

        # other optional flags
        if "referenceImpedance" in emxArgs:
            cmd.append(f"--s-impedance={emxArgs['referenceImpedance']}")
        
        if "parallelCPU" in emxArgs:
            cmd.append(f"--parallel={emxArgs['parallelCPU']}")
        if "simultaneousFrequencies" in emxArgs:
            cmd.append(f"--simultaneous-frequencies={emxArgs['simultaneousFrequencies']}")
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

        # output formats
        output_name = emxArgs.get("outputName", emxArgs["gdsCellName"])
        for fmt, use in emxArgs.get("SParam", {}).get("formats", {}).items():
            if fmt.lower() == "touchstone" and use:
                cmd += [
                    "--format", "touchstone",
                    "-s", os.path.join(remote_dir, f"{output_name}.s{port_count}p")
                ]
        for fmt, use in emxArgs.get("YParam", {}).get("formats", {}).items():
            if fmt.lower() == "touchstone" and use:
                cmd += [
                    "--format", "touchstone",
                    "-y", os.path.join(remote_dir, f"{output_name}.y{port_count}p")
                ]

        if "verbose" in emxArgs:
            cmd.append(f"--verbose={emxArgs['verbose']}")


        # -------------------------------------------------------------------
        # 4) Run EMX remotely
        # -------------------------------------------------------------------



        logger.critical(ssh_base + [" ".join(cmd)])
        subprocess.run(ssh_base + [" ".join(cmd)], check=True)
        logger.info("Remote EMX execution completed")

        # -------------------------------------------------------------------
        # 5) Fetch results
        # -------------------------------------------------------------------
        results = {}
        for ext in ("s", "y"):
            fname = f"{output_name}.{ext}{port_count}p"
            remote_path = f"{ssh_host}:{remote_dir}/{fname}"
            local_path  = os.path.join(emxArgs["outputPath"], fname)
            subprocess.run(scp_base + [remote_path, local_path], check=True)
            results[f"{ext}Params"] = local_path
            logger.info(f"Fetched {fname}")

        return results

    finally:
        # -------------------------------------------------------------------
        # 6) Always clean up remote temp dir
        # -------------------------------------------------------------------
        subprocess.run(ssh_base + [f"rm -rf {remote_dir}"], check=False)
        logger.info(f"Removed remote directory {remote_dir}")


def emx_local(emxArgs):
    """
    Constructs and executes the simulation command based on the provided arguments.
    Raises a ValueError if mandatory keys (e.g. sweep frequencies) are missing.
    """

    # # Dynamically set log level (default: "info")
    # log_levels = {
    #     "debug": logging.DEBUG,
    #     "info": logging.INFO,
    #     "warning": logging.WARNING,
    #     "error": logging.ERROR,
    #     "critical": logging.CRITICAL,
    #     "none": logging.CRITICAL + 10  # Effectively disables all logging
    # }   
    # log_level_str = emxArgs.get("logLevel", "info").lower()
    # log_level = log_levels.get(log_level_str, logging.INFO)
    # logger.setLevel(log_level)

    # # Ensure logger handler is attached
    # if not logger.handlers:
    #     handler = logging.StreamHandler()
    #     handler.setFormatter(ColorFormatter('%(asctime)s - %(levelname)s - %(message)s'))
    #     logger.addHandler(handler)

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

    logger.debug(f"Artwork parameters: {artworkData.get('parameters')}")
    emxConfigX["gdsCellName"] = artworkData["metadata"]["name"]
    emxConfigX["ports"] = artworkData["ports"]
    emxConfigX["designPorts"] = artworkData["ports"]
    emxConfigX["simulatingPorts"] = artworkData["ports"]["config"]["simulatingPorts"]

    try:
        emx(emxConfigX)
    except Exception as error:
        logger.error(f"Simulation failed")
        raise



