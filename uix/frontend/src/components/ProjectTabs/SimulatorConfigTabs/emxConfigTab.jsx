import React, { useState, useEffect } from 'react';

const defaultEmxConfig = {
  remote: {
        "use": false,
        "useProxy": false,
        "sshJump": "habiburr@login.uio.no",
        "sshHost": "habiburr@nano.ifi.uio.no"
      },
  emxPath: "/projects/nanus/eda/Cadence/2021/INTEGRAND60/bin/emx",
  emxProcPath: "RC_IRCX_CRN65LP_1P9M+ALRDL_6X1Z1U_typical.proc",
  sweepFreq: {
    startFreq: 1e6,
    stopFreq: 50e9,
    stepNum: 2000,
    stepSize: 10e6,
    useStepSize: false,
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
      psf: true,
    },
  },
  YParam: {
    formats: {
      touchstone: true,
      matlab: true,
      spectre: true,
      psf: true,
    },
  },
};

function EMXTab() {
  const [textValue, setTextValue] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch('/api/load_emx_config');
        const result = await res.json();

        if (!res.ok) throw new Error(result.error);
        const config = Object.keys(result.data || {}).length > 0
          ? result.data
          : defaultEmxConfig;

        setTextValue(JSON.stringify(config, null, 2));
      } catch (err) {
        console.error('Failed to load config:', err);
        setTextValue(JSON.stringify(defaultEmxConfig, null, 2));
      } finally {
        setIsLoading(false);
      }
    };

    fetchConfig();
  }, []);

  const handleChange = (e) => {
    setTextValue(e.target.value);
  };

  const handleSave = async () => {
    try {
      const parsed = JSON.parse(textValue);
      setIsSaving(true);
      const res = await fetch('/api/save_emx_config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      });
      const result = await res.json();
      setIsSaving(false);
      if (!res.ok) throw new Error(result.error);
      alert('✅ EMX config saved successfully!');
    } catch (err) {
      console.error(err);
      setIsSaving(false);
      alert('❌ Failed to save EMX config: ' + err.message);
    }
  };

  return (
    <div>
      <h4>🧪 EMX Simulator Config (Editable JSON)</h4>
      {isLoading ? (
        <p>Loading config...</p>
      ) : (
        <>
          <textarea
            value={textValue}
            onChange={handleChange}
            style={{
              width: '100%',
              height: '500px',
              fontFamily: 'monospace',
              fontSize: '14px',
              padding: '10px',
              borderRadius: '8px',
              border: '1px solid #ccc',
            }}
          />
          <div style={{ marginTop: '10px' }}>
            <button onClick={handleSave} disabled={isSaving}>
              {isSaving ? 'Saving...' : '💾 Save Config'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default EMXTab;
