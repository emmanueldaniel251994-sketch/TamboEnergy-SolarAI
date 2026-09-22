import { useEffect, useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";

function Diagnostics({ token }) {
  const [telemetryRecords, setTelemetryRecords] = useState([]);
  const [selectedTelemetryId, setSelectedTelemetryId] = useState("");
  const [diagnostic, setDiagnostic] = useState(null);

  const [loadingTelemetry, setLoadingTelemetry] = useState(true);
  const [loadingDiagnostic, setLoadingDiagnostic] = useState(false);
  const [deletingDiagnostic, setDeletingDiagnostic] = useState(false);

  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState("");

  // ============================================================
  // FETCH TELEMETRY
  // ============================================================

  const fetchTelemetry = async () => {
    setLoadingTelemetry(true);
    setMessage("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/telemetry/`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to load telemetry records."
        );
      }

      const records = Array.isArray(data) ? data : [];

      // Show newest telemetry first.
      records.sort(
        (a, b) => Number(b.id) - Number(a.id)
      );

      setTelemetryRecords(records);

      // If there are no telemetry records left,
      // clear the selector and diagnostic.
      if (records.length === 0) {
        setSelectedTelemetryId("");
        setDiagnostic(null);
        return records;
      }

      // Check whether the currently selected record
      // still exists.
      const selectedStillExists = records.some(
        (record) =>
          String(record.id) === String(selectedTelemetryId)
      );

      if (
        !selectedTelemetryId ||
        !selectedStillExists
      ) {
        setSelectedTelemetryId(
          String(records[0].id)
        );
      }

      return records;

    } catch (error) {
      setMessage(error.message);
      return [];
    } finally {
      setLoadingTelemetry(false);
    }
  };

  // ============================================================
  // FETCH DIAGNOSTIC
  // ============================================================

  const fetchDiagnostic = async (telemetryId) => {
    if (!telemetryId) {
      setMessage(
        "Please select a telemetry record."
      );
      return;
    }

    setLoadingDiagnostic(true);
    setMessage("");
    setSuccess("");
    setDiagnostic(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/diagnostics/telemetry/${telemetryId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Unable to generate diagnostic."
        );
      }

      setDiagnostic(data);

    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoadingDiagnostic(false);
    }
  };

  // ============================================================
  // DELETE DIAGNOSTIC / TELEMETRY
  // Admin Only
  // ============================================================

  const handleDeleteDiagnostic = async () => {
    if (!selectedTelemetryId) {
      setMessage(
        "Please select a telemetry record."
      );
      return;
    }

    const selectedRecord =
      telemetryRecords.find(
        (record) =>
          String(record.id) ===
          String(selectedTelemetryId)
      );

    const solarSystemId =
      selectedRecord?.solar_system_id ||
      diagnostic?.solar_system_id ||
      "Unknown";

    const confirmed = window.confirm(
      `Permanently delete Telemetry #${selectedTelemetryId}?\n\n` +
      `Solar System #${solarSystemId}\n\n` +
      "This will also delete its diagnostic data and any alert directly linked to this telemetry record.\n\n" +
      "This action cannot be undone."
    );

    if (!confirmed) {
      return;
    }

    setDeletingDiagnostic(true);
    setMessage("");
    setSuccess("");

    try {
      const deletedTelemetryId =
        selectedTelemetryId;

      const response = await fetch(
        `${API_BASE_URL}/telemetry/${deletedTelemetryId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      let data = {};

      try {
        data = await response.json();
      } catch {
        // Response may not contain JSON.
      }

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Unable to delete diagnostic."
        );
      }

      // Remove deleted telemetry immediately
      // from the local list.
      const remainingRecords =
        telemetryRecords.filter(
          (record) =>
            String(record.id) !==
            String(deletedTelemetryId)
        );

      setTelemetryRecords(
        remainingRecords
      );

      // Remove diagnostic currently displayed.
      setDiagnostic(null);

      // Automatically select the next available
      // telemetry record.
      if (remainingRecords.length > 0) {
        setSelectedTelemetryId(
          String(remainingRecords[0].id)
        );
      } else {
        setSelectedTelemetryId("");
      }

      const deletedAlerts =
        Array.isArray(data.deleted_alert_ids)
          ? data.deleted_alert_ids
          : [];

      if (deletedAlerts.length > 0) {
        setSuccess(
          `Telemetry #${deletedTelemetryId} and its diagnostic were deleted successfully. ` +
          `${deletedAlerts.length} linked alert${
            deletedAlerts.length === 1 ? "" : "s"
          } also deleted.`
        );
      } else {
        setSuccess(
          `Telemetry #${deletedTelemetryId} and its diagnostic were deleted successfully.`
        );
      }

    } catch (error) {
      setMessage(error.message);
    } finally {
      setDeletingDiagnostic(false);
    }
  };

  // ============================================================
  // HANDLE TELEMETRY SELECTION
  // ============================================================

  const handleTelemetryChange = (event) => {
    const newTelemetryId =
      event.target.value;

    setSelectedTelemetryId(
      newTelemetryId
    );

    // Do not continue showing the previous
    // telemetry's diagnostic.
    setDiagnostic(null);
    setMessage("");
    setSuccess("");
  };

  // ============================================================
  // INITIAL LOAD
  // ============================================================

  useEffect(() => {
    fetchTelemetry();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ============================================================
  // FORMAT HELPERS
  // ============================================================

  const formatDate = (date) => {
    if (!date) {
      return "—";
    }

    const parsedDate = new Date(date);

    if (Number.isNaN(parsedDate.getTime())) {
      return date;
    }

    return parsedDate.toLocaleString();
  };

  const formatConfidence = (confidence) => {
    if (
      confidence === null ||
      confidence === undefined
    ) {
      return "Not available";
    }

    return `${(
      Number(confidence) * 100
    ).toFixed(1)}%`;
  };

  const formatValue = (
    value,
    unit = ""
  ) => {
    if (
      value === null ||
      value === undefined
    ) {
      return "—";
    }

    return `${value}${unit}`;
  };

  // ============================================================
  // PAGE
  // ============================================================

  return (
    <div className="diagnostics-page">

      {/* HEADER */}

      <div className="page-header">
        <div>
          <h1>AI Diagnostics</h1>

          <p>
            Analyse solar telemetry using TamboEnergy
            SolarAI fault detection and machine-learning
            diagnostics.
          </p>
        </div>

        <button
          type="button"
          className="secondary-button"
          onClick={fetchTelemetry}
          disabled={
            loadingTelemetry ||
            deletingDiagnostic
          }
        >
          {loadingTelemetry
            ? "Refreshing..."
            : "Refresh Telemetry"}
        </button>
      </div>

      {/* ERROR */}

      {message && (
        <div className="diagnostic-message">
          {message}
        </div>
      )}

      {/* SUCCESS */}

      {success && (
        <div className="success-message">
          {success}
        </div>
      )}

      {/* TELEMETRY SELECTOR */}

      <div className="diagnostic-selector-card">

        <div className="diagnostic-selector">

          <div>
            <label htmlFor="telemetry-select">
              Telemetry Record
            </label>

            <select
              id="telemetry-select"
              value={selectedTelemetryId}
              onChange={
                handleTelemetryChange
              }
              disabled={
                loadingTelemetry ||
                deletingDiagnostic
              }
            >
              <option value="">
                Select telemetry
              </option>

              {telemetryRecords.map(
                (record) => (
                  <option
                    key={record.id}
                    value={record.id}
                  >
                    Telemetry #{record.id}
                    {" — "}
                    System #{record.solar_system_id}
                    {" — "}
                    {record.final_diagnosis ||
                      record.status}
                  </option>
                )
              )}
            </select>
          </div>

          {/* RUN DIAGNOSTIC */}

          <button
            type="button"
            className="primary-button"
            onClick={() =>
              fetchDiagnostic(
                selectedTelemetryId
              )
            }
            disabled={
              !selectedTelemetryId ||
              loadingDiagnostic ||
              deletingDiagnostic
            }
          >
            {loadingDiagnostic
              ? "Analysing..."
              : "Run Diagnostic"}
          </button>

          {/* DELETE DIAGNOSTIC */}

          <button
            type="button"
            className="delete-button"
            onClick={
              handleDeleteDiagnostic
            }
            disabled={
              !selectedTelemetryId ||
              loadingDiagnostic ||
              deletingDiagnostic
            }
          >
            {deletingDiagnostic
              ? "Deleting..."
              : "Delete Diagnostic"}
          </button>

        </div>

        <p className="diagnostic-record-count">
          {telemetryRecords.length} telemetry record
          {telemetryRecords.length === 1
            ? ""
            : "s"}{" "}
          available
        </p>

      </div>

      {/* EMPTY STATE */}

      {!diagnostic &&
        !loadingDiagnostic && (
          <div className="diagnostic-empty-state">
            <h3>
              Select telemetry to analyse
            </h3>

            <p>
              Choose a telemetry record above
              and click
              <strong>
                {" "}Run Diagnostic
              </strong>.
            </p>
          </div>
        )}

      {/* LOADING DIAGNOSTIC */}

      {loadingDiagnostic && (
        <div className="diagnostic-empty-state">
          <h3>
            SolarAI is analysing telemetry...
          </h3>

          <p>
            Comparing rule-based fault detection
            and machine-learning predictions.
          </p>
        </div>
      )}

      {/* DIAGNOSTIC RESULT */}

      {diagnostic &&
        !loadingDiagnostic && (
          <>

            {/* MAIN DIAGNOSIS */}

            <div className="diagnostic-result-card">

              <div className="diagnostic-result-heading">

                <div>
                  <span className="diagnostic-label">
                    FINAL DIAGNOSIS
                  </span>

                  <h2>
                    {
                      diagnostic.diagnostic
                        .title
                    }
                  </h2>
                </div>

                <div className="diagnostic-badges">

                  <span
                    className={`diagnostic-priority priority-${diagnostic.diagnostic.priority}`}
                  >
                    {
                      diagnostic.diagnostic
                        .priority
                    }{" "}
                    priority
                  </span>

                  {diagnostic.analysis
                    .needs_review === 1 && (
                    <span className="review-badge">
                      Needs Review
                    </span>
                  )}

                </div>

              </div>

              <p className="diagnostic-explanation">
                {
                  diagnostic.diagnostic
                    .explanation
                }
              </p>

              <div className="recommended-action">
                <strong>
                  Recommended Action
                </strong>

                <p>
                  {
                    diagnostic.diagnostic
                      .recommended_action
                  }
                </p>
              </div>

              {diagnostic.diagnostic
                .possible_causes?.length >
                0 && (
                <div className="possible-causes">

                  <strong>
                    Possible Causes
                  </strong>

                  <ul>
                    {diagnostic.diagnostic
                      .possible_causes.map(
                        (cause, index) => (
                          <li key={index}>
                            {cause}
                          </li>
                        )
                      )}
                  </ul>

                </div>
              )}

            </div>

            {/* AI ANALYSIS */}

            <div className="diagnostic-section">

              <h3>AI Analysis</h3>

              <div className="diagnostic-analysis-grid">

                <div className="analysis-card">
                  <span>
                    Rule Prediction
                  </span>

                  <strong>
                    {
                      diagnostic.analysis
                        .rule_prediction
                    }
                  </strong>
                </div>

                <div className="analysis-card">
                  <span>
                    Rule Severity
                  </span>

                  <strong>
                    {
                      diagnostic.analysis
                        .rule_severity
                    }
                  </strong>
                </div>

                <div className="analysis-card">
                  <span>
                    ML Prediction
                  </span>

                  <strong>
                    {diagnostic.analysis
                      .ml_prediction ||
                      "Not available"}
                  </strong>
                </div>

                <div className="analysis-card">
                  <span>
                    ML Confidence
                  </span>

                  <strong>
                    {formatConfidence(
                      diagnostic.analysis
                        .ml_confidence
                    )}
                  </strong>
                </div>

                <div className="analysis-card">
                  <span>
                    Prediction Agreement
                  </span>

                  <strong>
                    {
                      diagnostic.analysis
                        .prediction_agreement
                    }
                  </strong>
                </div>

                <div className="analysis-card">
                  <span>
                    Final Diagnosis
                  </span>

                  <strong>
                    {
                      diagnostic.analysis
                        .final_diagnosis
                    }
                  </strong>
                </div>

              </div>

              <div className="review-message">
                <strong>
                  Review Status
                </strong>

                <p>
                  {
                    diagnostic.analysis
                      .review_message
                  }
                </p>
              </div>

            </div>

            {/* TELEMETRY MEASUREMENTS */}

            <div className="diagnostic-section">

              <div className="diagnostic-section-heading">

                <div>
                  <h3>
                    Telemetry Measurements
                  </h3>

                  <p>
                    Solar System #
                    {
                      diagnostic.solar_system_id
                    }
                    {" • "}
                    Telemetry #
                    {
                      diagnostic.telemetry_id
                    }
                  </p>
                </div>

                <span className="telemetry-time">
                  {formatDate(
                    diagnostic.telemetry
                      .created_at
                  )}
                </span>

              </div>

              <div className="telemetry-grid">

                <div className="telemetry-card">
                  <span>
                    PV Voltage
                  </span>

                  <strong>
                    {formatValue(
                      diagnostic.telemetry
                        .pv_voltage,
                      " V"
                    )}
                  </strong>
                </div>

                <div className="telemetry-card">
                  <span>
                    PV Current
                  </span>

                  <strong>
                    {formatValue(
                      diagnostic.telemetry
                        .pv_current,
                      " A"
                    )}
                  </strong>
                </div>

                <div className="telemetry-card">
                  <span>
                    PV Power
                  </span>

                  <strong>
                    {formatValue(
                      diagnostic.telemetry
                        .pv_power,
                      " W"
                    )}
                  </strong>
                </div>

                <div className="telemetry-card">
                  <span>
                    Battery Voltage
                  </span>

                  <strong>
                    {formatValue(
                      diagnostic.telemetry
                        .battery_voltage,
                      " V"
                    )}
                  </strong>
                </div>

                <div className="telemetry-card">
                  <span>
                    Battery Current
                  </span>

                  <strong>
                    {formatValue(
                      diagnostic.telemetry
                        .battery_current,
                      " A"
                    )}
                  </strong>
                </div>

                <div className="telemetry-card">
                  <span>
                    Battery SOC
                  </span>

                  <strong>
                    {formatValue(
                      diagnostic.telemetry
                        .battery_soc,
                      "%"
                    )}
                  </strong>
                </div>

                <div className="telemetry-card">
                  <span>
                    Load Power
                  </span>

                  <strong>
                    {formatValue(
                      diagnostic.telemetry
                        .load_power,
                      " W"
                    )}
                  </strong>
                </div>

                <div className="telemetry-card">
                  <span>
                    Temperature
                  </span>

                  <strong>
                    {formatValue(
                      diagnostic.telemetry
                        .temperature,
                      " °C"
                    )}
                  </strong>
                </div>

                <div className="telemetry-card">
                  <span>
                    Error Code
                  </span>

                  <strong>
                    {diagnostic.telemetry
                      .error_code ||
                      "None"}
                  </strong>
                </div>

              </div>

            </div>

          </>
        )}

    </div>
  );
}

export default Diagnostics;