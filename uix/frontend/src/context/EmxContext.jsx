import { createContext, useContext, useState } from 'react';

const EmxContext = createContext();

const defaultEmxConfig = {
  emxPath: "/projects/nanus/eda/Cadence/2021/INTEGRAND60/bin/emx",
  emxProcPath: "RC_IRCX_CRN65LP_1P9M+ALRDL_6X1Z1U_typical.proc",
  sweepFreq: {
    startFreq: 1e6,
    stopFreq: 50e9,
    stepNum: 2000,
    stepSize: 10e6,
    useStepSize: false
  },
  referenceImpedance: 100,
  edgeWidth: 1,
  "3dCond": true,
  sidewalls: false,
  viaSidewalls: false,
  viaInductance: false,
  viaEdgeFactor: 1,
  thickness: 1,
  useCadencePins: false,
  viaSeparation: 0.5,
  labelDepth: 2,
  InductiveOnly: false,
  CapacitiveOnly: false,
  ResistiveOnly: false,
  ResistiveAndCapacitiveOnly: false,
  dumpConnectivity: true,
  quasistatic: true,
  fullwave: false,
  parallelCPU: 128,
  simultaneousFrequencies: 0,
  recommendedMemory: true,
  verbose: 3,
  printCommandLine: true,
  format: "touchstone",
  SParam: {
    formats: {
      touchstone: true,
      matlab: true,
      spectre: true,
      psf: true
    }
  },
  YParam: {
    formats: {
      touchstone: true,
      matlab: true,
      spectre: true,
      psf: true
    }
  }
};

export const EmxProvider = ({ children }) => {
  const [emxConfig, setEmxConfig] = useState(defaultEmxConfig);

  return (
    <EmxContext.Provider value={{ emxConfig, setEmxConfig }}>
      {children}
    </EmxContext.Provider>
  );
};

export const useEmxContext = () => useContext(EmxContext);
