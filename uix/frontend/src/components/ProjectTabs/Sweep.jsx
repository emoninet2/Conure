import React, { useState, useEffect } from 'react';
import { useSweep } from '../../context/SweepContext';
import { useArtworkContext } from '../../context/ArtworkContext';
import { listSweeps, loadSweep, processLoadedSweep } from '../../services/api';
import '../../styles/theme.css';

const Sweep = () => {
  const {
    mode, sweepName, sweepParams,
    setSweepParams, handleModeChange,
    handleSweepNameChange, addRow,
    deleteRow, handleRowChange, handleSave
  } = useSweep();

  const { parameter: { parameterData } } = useArtworkContext();
  const [sweepOptions, setSweepOptions] = useState([]);

  useEffect(() => {
    if (mode === 'open') {
      const fetchSweeps = async () => {
        try {
          const result = await listSweeps();
          if (result.success && result.sweeps) {
            setSweepOptions(result.sweeps);
          }
        } catch (error) {
          console.error("Error fetching sweeps:", error);
        }
      };
      fetchSweeps();
    }
  }, [mode]);

  useEffect(() => {
    if (mode === 'open' && sweepName) {
      const fetchSweepDetails = async () => {
        try {
          const response = await loadSweep(sweepName);
          const { sweepParams: loadedSweepParams } = processLoadedSweep(response);
          setSweepParams(loadedSweepParams);
        } catch (error) {
          console.error("Error loading sweep details:", error);
        }
      };
      fetchSweepDetails();
    }
  }, [sweepName, mode, setSweepParams]);

  return (
    <div className="artwork-subtab-container">
      <h4 className="section-heading">🌀 Sweep</h4>

      {/* Mode Toggle */}
      <div className="mode-selection">
        <label className="mode-label">
          <input
            type="radio"
            name="mode"
            value="new"
            checked={mode === "new"}
            onChange={handleModeChange}
          />
          Create New Sweep
        </label>
        <label className="mode-label">
          <input
            type="radio"
            name="mode"
            value="open"
            checked={mode === "open"}
            onChange={handleModeChange}
          />
          Open Existing Sweep
        </label>
      </div>

      {/* Sweep Name Input/Select */}
      <div className="input-group">
        {mode === "new" ? (
          <label>
            Enter new sweep name:
            <input
              type="text"
              value={sweepName}
              onChange={handleSweepNameChange}
              className="input-field"
              placeholder="New Sweep Name"
            />
          </label>
        ) : (
          <label>
            Select sweep data:
            <select
              value={sweepName}
              onChange={handleSweepNameChange}
              className="input-field"
            >
              <option value="">-- Select Sweep Data --</option>
              {sweepOptions.map((option) => (
                <option key={option.sweep_name} value={option.sweep_name}>
                  {option.sweep_name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {sweepName && (
        <div className="input-group">
          <strong>Current Sweep:</strong> {sweepName}
        </div>
      )}

      {/* Save Button */}
      <div className="button-group">
        <button onClick={handleSave} className="btn primary">
          💾 Save Sweep
        </button>
      </div>

      {/* Table */}
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Parameter Name</th>
            <th>From</th>
            <th>To</th>
            <th>Type</th>
            <th>nPoints / Step</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sweepParams.length > 0 ? (
            sweepParams.map((row, index) => {
              const otherSelected = sweepParams
                .filter((_, i) => i !== index)
                .map(r => r.parameterName);
              const availableOptions = parameterData.filter(
                item => !otherSelected.includes(item.parameter) || item.parameter === row.parameterName
              );
              return (
                <tr key={index}>
                  <td>
                    <select
                      value={row.parameterName}
                      onChange={(e) => handleRowChange(index, "parameterName", e.target.value)}
                      className="input-field"
                    >
                      <option value="">-- Select --</option>
                      {availableOptions.map((item, i) => (
                        <option key={i} value={item.parameter}>{item.parameter}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      value={row.from}
                      onChange={(e) => handleRowChange(index, "from", e.target.value)}
                      className="input-field"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={row.to}
                      onChange={(e) => handleRowChange(index, "to", e.target.value)}
                      className="input-field"
                    />
                  </td>
                  <td>
                    <select
                      value={row.type}
                      onChange={(e) => handleRowChange(index, "type", e.target.value)}
                      className="input-field"
                    >
                      <option value="npoints">nPoints</option>
                      <option value="step">Step</option>
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      value={row.value}
                      onChange={(e) => handleRowChange(index, "value", e.target.value)}
                      className="input-field"
                    />
                  </td>
                  <td>
                    <button
                      onClick={() => deleteRow(index)}
                      className="btn-table-action delete"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan="6" className="centered">
                No parameters available.
              </td>
            </tr>
          )}
        </tbody>
      </table>

        <button onClick={addRow} className="btn-table-action add" style={{ display: 'block' }}>
          ➕ Add Row
        </button>

    </div>
  );
};

export default Sweep;
