# Configuring EMX for Local and Remote Execution with Conure

This document explains how to configure `emx` to run locally or remotely through SSH, including multi-hop (jump host) scenarios. This is intended for users of the Conure environment.

## Running EMX Locally

If you want to run EMX locally on your machine without remote access, set the configuration like this:

```json
{
  "emx_config": {
    "remote": {
      "use": false,
      "sshJump": "",
      "sshHost": ""
    },
    "logLevel": "info",
    "emxPath": "/path/to/emx",
    "emxProcPath": "/path/to/proc/file.proc",
    "sweepFreq": {
      "startFreq": 1000000,
      "stopFreq": 50000000000,
      "stepNum": 3000,
      "stepSize": 10000000,
      "useStepSize": false
    },
    "referenceImpedance": 100,
    "edgeWidth": 1,
    "3dCond": true,
    "sidewalls": false,
    "viaSidewalls": false,
    "viaInductance": false,
    "viaEdgeFactor": 1,
    "thickness": 1,
    "useCadencePins": false,
    "viaSeparation": 0.5,
    "labelDepth": 2,
    "InductiveOnly": false,
    "CapacitiveOnly": false,
    "ResistiveOnly": false,
    "ResistiveAndCapacitiveOnly": false,
    "dumpConnectivity": true,
    "quasistatic": true,
    "fullwave": false,
    "parallelCPU": 128,
    "simultaneousFrequencies": 0,
    "recommendedMemory": true,
    "verbose": 0,
    "printCommandLine": true,
    "format": "touchstone",
    "SParam": {
      "formats": {
        "touchstone": true,
        "matlab": true,
        "spectre": true,
        "psf": true
      }
    },
    "YParam": {
      "formats": {
        "touchstone": true,
        "matlab": true,
        "spectre": true,
        "psf": true
      }
    }
  }
}
```

## Setting Up Remote EMX Execution

If you need to run `emx` remotely through SSH, follow these steps to configure passwordless access and update your configuration accordingly.

### 1. Generate an SSH Key Pair

Generate a new SSH key on your local machine:

```bash
ssh-keygen -t ed25519 -C "emx_remote"
```

- Press `Enter` to accept the default file location.
- Leave the passphrase blank for automation purposes.

### 2. Copy SSH Public Key to Jump Hosts

If you have multiple jump hosts, copy your public key to each jump host sequentially:

**Single Jump Host Example:**

```bash
ssh-copy-id user@jump.example.com
```

**Multiple Jump Hosts Example:**

Repeat this step for each jump host:

```bash
ssh-copy-id user@jump1.example.com
ssh-copy-id -o ProxyJump=user@jump1.example.com user@jump2.example.com
# Continue as necessary...
```

### 3. Copy SSH Public Key to the Target Host via Jump Host(s)

Copy your public key to the target host using your jump host(s):

**Single Jump Host:**

```bash
ssh-copy-id -o ProxyJump=user@jump.example.com user@target.example.com
```

**Multiple Jump Hosts:**

For multiple jumps, chain hosts separated by commas:

```bash
ssh-copy-id -o ProxyJump=user@jump1.example.com,user@jump2.example.com user@target.example.com
```

### 4. Test Passwordless Access and EMX Execution

Ensure you can run `emx` remotely without entering a password:

**Single Jump Host:**

```bash
ssh -J user@jump.example.com user@target.example.com emx --version
```

**Multiple Jump Hosts:**

```bash
ssh -J user@jump1.example.com,user@jump2.example.com user@target.example.com emx --version
```

If configured correctly, `emx` should run remotely without prompting for passwords.

## Remote EMX Configuration Example

> **Note:** When running EMX remotely, make sure that the specified `.proc` file (e.g., `/path/to/remote/proc/file.proc`) is present on the remote target server and accessible by the user.

Once SSH access is configured, update your `emx_config` like this to enable remote execution:

```json
{
  "emx_config": {
    "remote": {
      "use": true,
      "sshJump": "user@jump.example.com",
      "sshHost": "user@target.example.com"
    },
    "logLevel": "info",
    "emxPath": "/path/to/emx",
    "emxProcPath": "/path/to/remote/proc/file.proc",
    "sweepFreq": {
      "startFreq": 1000000,
      "stopFreq": 50000000000,
      "stepNum": 3000,
      "stepSize": 10000000,
      "useStepSize": false
    },
    "referenceImpedance": 100,
    "edgeWidth": 1,
    "3dCond": true,
    "sidewalls": false,
    "viaSidewalls": false,
    "viaInductance": false,
    "viaEdgeFactor": 1,
    "thickness": 1,
    "useCadencePins": false,
    "viaSeparation": 0.5,
    "labelDepth": 2,
    "InductiveOnly": false,
    "CapacitiveOnly": false,
    "ResistiveOnly": false,
    "ResistiveAndCapacitiveOnly": false,
    "dumpConnectivity": true,
    "quasistatic": true,
    "fullwave": false,
    "parallelCPU": 128,
    "simultaneousFrequencies": 0,
    "recommendedMemory": true,
    "verbose": 0,
    "printCommandLine": true,
    "format": "touchstone",
    "SParam": {
      "formats": {
        "touchstone": true,
        "matlab": true,
        "spectre": true,
        "psf": true
      }
    },
    "YParam": {
      "formats": {
        "touchstone": true,
        "matlab": true,
        "spectre": true,
        "psf": true
      }
    }
  }
}
```
