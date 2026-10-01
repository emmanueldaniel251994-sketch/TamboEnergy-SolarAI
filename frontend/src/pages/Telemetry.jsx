import { useCallback, useEffect, useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";

function Telemetry({ token }) {
    const [solarSystems, setSolarSystems] = useState([]);
    const [selectedSystemId, setSelectedSystemId] = useState("");
    const [telemetry, setTelemetry] = useState(null);

    const [loadingSystems, setLoadingSystems] = useState(true);
    const [loadingTelemetry, setLoadingTelemetry] = useState(false);

    const [error, setError] = useState("");
    const [lastRefreshed, setLastRefreshed] = useState(null);

    // ============================================================
    // HELPERS
    // ============================================================

    const authHeaders = {
        Authorization: `Bearer ${token}`,
    };

    const displayValue = (value, unit = "") => {
        if (value === null || value === undefined || value === "") {
            return "—";
        }

        return `${value}${unit}`;
    };

    const formatDate = (value) => {
        if (!value) {
            return "—";
        }

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return value;
        }

        return date.toLocaleString();
    };

    const formatLabel = (value) => {
        if (!value) {
            return "Unknown";
        }

        return String(value)
            .replaceAll("_", " ")
            .replace(/\b\w/g, (letter) => letter.toUpperCase());
    };

    const confidencePercentage = (value) => {
        if (value === null || value === undefined) {
            return "—";
        }

        return `${(Number(value) * 100).toFixed(1)}%`;
    };

    // ============================================================
    // LOAD SOLAR SYSTEMS
    // ============================================================

    const loadSolarSystems = useCallback(async () => {
        setLoadingSystems(true);
        setError("");

        try {
            const response = await fetch(
                `${API_BASE_URL}/solar-systems/`,
                {
                    headers: authHeaders,
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Unable to load solar systems."
                );
            }

            const systems = Array.isArray(data) ? data : [];

            setSolarSystems(systems);

            if (systems.length > 0) {
                setSelectedSystemId((current) => {
                    const exists = systems.some(
                        (system) =>
                            String(system.id) === String(current)
                    );

                    if (current && exists) {
                        return current;
                    }

                    return String(systems[0].id);
                });
            } else {
                setSelectedSystemId("");
                setTelemetry(null);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoadingSystems(false);
        }
    }, [token]);

    // ============================================================
    // LOAD LATEST TELEMETRY
    // ============================================================

    const loadLatestTelemetry = useCallback(
        async (systemId, showLoading = true) => {
            if (!systemId) {
                return;
            }

            if (showLoading) {
                setLoadingTelemetry(true);
            }

            setError("");

            try {
                const response = await fetch(
                    `${API_BASE_URL}/telemetry/latest/${systemId}`,
                    {
                        headers: authHeaders,
                    }
                );

                if (response.status === 404) {
                    setTelemetry(null);
                    setLastRefreshed(new Date());
                    return;
                }

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(
                        data.detail ||
                        "Unable to load latest telemetry."
                    );
                }

                setTelemetry(data);
                setLastRefreshed(new Date());
            } catch (err) {
                setError(err.message);
            } finally {
                if (showLoading) {
                    setLoadingTelemetry(false);
                }
            }
        },
        [token]
    );

    // ============================================================
    // INITIAL LOAD
    // ============================================================

    useEffect(() => {
        loadSolarSystems();
    }, [loadSolarSystems]);

    useEffect(() => {
        if (!selectedSystemId) {
            return;
        }

        setTelemetry(null);
        loadLatestTelemetry(selectedSystemId);
    }, [selectedSystemId, loadLatestTelemetry]);

    // ============================================================
    // AUTO REFRESH
    // Refresh every 30 seconds while this page is mounted.
    // ============================================================

    useEffect(() => {
        if (!selectedSystemId) {
            return undefined;
        }

        const interval = setInterval(() => {
            loadLatestTelemetry(selectedSystemId, false);
        }, 30000);

        return () => clearInterval(interval);
    }, [selectedSystemId, loadLatestTelemetry]);

    // ============================================================
    // STATUS
    // ============================================================

    const diagnosis =
        telemetry?.final_diagnosis ||
        telemetry?.fault_type ||
        telemetry?.status ||
        "unknown";

    const statusClass = String(
        telemetry?.status || "unknown"
    )
        .toLowerCase()
        .replaceAll(" ", "_");

    const needsReview =
        Number(telemetry?.needs_review) === 1;

    // ============================================================
    // PAGE
    // ============================================================

    return (
        <div className="telemetry-page">
            {/* HEADER */}

            <div className="page-header">
                <div>
                    <h1>Live Monitoring</h1>

                    <p>
                        Monitor the latest operating data from your
                        solar energy systems.
                    </p>
                </div>

                <button
                    type="button"
                    className="secondary-button"
                    disabled={
                        !selectedSystemId || loadingTelemetry
                    }
                    onClick={() =>
                        loadLatestTelemetry(selectedSystemId)
                    }
                >
                    {loadingTelemetry
                        ? "Refreshing..."
                        : "Refresh Data"}
                </button>
            </div>

            {/* ERROR */}

            {error && (
                <div className="diagnostic-message">
                    {error}
                </div>
            )}

            {/* SYSTEM SELECTOR */}

            <div className="telemetry-selector-card">
                <div className="telemetry-selector">
                    <div className="telemetry-selector-field">
                        <label htmlFor="telemetry-system">
                            Solar System
                        </label>

                        <select
                            id="telemetry-system"
                            value={selectedSystemId}
                            disabled={loadingSystems}
                            onChange={(event) => {
                                setSelectedSystemId(event.target.value);
                                setError("");
                            }}
                        >
                            <option value="">
                                Select solar system
                            </option>

                            {solarSystems.map((system) => (
                                <option
                                    key={system.id}
                                    value={system.id}
                                >
                                    System #{system.id}
                                    {system.location
                                        ? ` — ${system.location}`
                                        : ""}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="telemetry-refresh-info">
                        <span>Auto Refresh</span>
                        <strong>Every 30 seconds</strong>

                        {lastRefreshed && (
                            <small>
                                Last checked:{" "}
                                {lastRefreshed.toLocaleTimeString()}
                            </small>
                        )}
                    </div>
                </div>
            </div>

            {/* NO SYSTEMS */}

            {!loadingSystems &&
                solarSystems.length === 0 && (
                    <div className="diagnostic-empty-state">
                        <h3>No solar systems available</h3>

                        <p>
                            Register a solar system before using live
                            monitoring.
                        </p>
                    </div>
                )}

            {/* LOADING */}

            {loadingTelemetry && (
                <div className="diagnostic-empty-state">
                    <h3>Loading telemetry...</h3>

                    <p>
                        SolarAI is retrieving the latest system
                        readings.
                    </p>
                </div>
            )}

            {/* NO TELEMETRY */}

            {!loadingTelemetry &&
                selectedSystemId &&
                !telemetry &&
                !error && (
                    <div className="diagnostic-empty-state">
                        <h3>No telemetry available</h3>

                        <p>
                            Solar System #{selectedSystemId} has not
                            reported telemetry data yet.
                        </p>
                    </div>
                )}

            {/* TELEMETRY */}

            {!loadingTelemetry && telemetry && (
                <>
                    {/* SYSTEM STATUS */}

                    <section className="telemetry-status-card">
                        <div>
                            <span className="telemetry-label">
                                SYSTEM STATUS
                            </span>

                            <h2>
                                Solar System #{telemetry.solar_system_id}
                            </h2>

                            <p>
                                Latest reading:{" "}
                                {formatDate(telemetry.created_at)}
                            </p>
                        </div>

                        <div className="telemetry-status-right">
                            <span
                                className={`telemetry-status-badge status-${statusClass}`}
                            >
                                {formatLabel(telemetry.status)}
                            </span>

                            {needsReview && (
                                <span className="telemetry-review-badge">
                                    Technician Review Required
                                </span>
                            )}
                        </div>
                    </section>

                    {/* MAIN ELECTRICAL READINGS */}

                    <section className="telemetry-section">
                        <div className="telemetry-section-heading">
                            <div>
                                <h2>Electrical Performance</h2>

                                <p>
                                    Latest PV, battery and load measurements.
                                </p>
                            </div>
                        </div>

                        <div className="telemetry-metric-grid">
                            <div className="telemetry-metric-card">
                                <span>PV Voltage</span>

                                <strong>
                                    {displayValue(
                                        telemetry.pv_voltage,
                                        " V"
                                    )}
                                </strong>
                            </div>

                            <div className="telemetry-metric-card">
                                <span>PV Current</span>

                                <strong>
                                    {displayValue(
                                        telemetry.pv_current,
                                        " A"
                                    )}
                                </strong>
                            </div>

                            <div className="telemetry-metric-card">
                                <span>PV Power</span>

                                <strong>
                                    {displayValue(
                                        telemetry.pv_power,
                                        " W"
                                    )}
                                </strong>
                            </div>

                            <div className="telemetry-metric-card">
                                <span>Load Power</span>

                                <strong>
                                    {displayValue(
                                        telemetry.load_power,
                                        " W"
                                    )}
                                </strong>
                            </div>

                            <div className="telemetry-metric-card">
                                <span>Battery Voltage</span>

                                <strong>
                                    {displayValue(
                                        telemetry.battery_voltage,
                                        " V"
                                    )}
                                </strong>
                            </div>

                            <div className="telemetry-metric-card">
                                <span>Battery Current</span>

                                <strong>
                                    {displayValue(
                                        telemetry.battery_current,
                                        " A"
                                    )}
                                </strong>
                            </div>

                            <div className="telemetry-metric-card battery-card">
                                <span>Battery SOC</span>

                                <strong>
                                    {displayValue(
                                        telemetry.battery_soc,
                                        "%"
                                    )}
                                </strong>

                                <div className="soc-progress">
                                    <div
                                        className="soc-progress-bar"
                                        style={{
                                            width: `${Math.min(
                                                100,
                                                Math.max(
                                                    0,
                                                    Number(
                                                        telemetry.battery_soc || 0
                                                    )
                                                )
                                            )}%`,
                                        }}
                                    />
                                </div>
                            </div>

                            <div className="telemetry-metric-card">
                                <span>Temperature</span>

                                <strong>
                                    {displayValue(
                                        telemetry.temperature,
                                        " °C"
                                    )}
                                </strong>
                            </div>
                        </div>
                    </section>

                    {/* AI DIAGNOSTIC */}

                    <section className="telemetry-section">
                        <div className="telemetry-section-heading">
                            <div>
                                <h2>SolarAI Diagnostic</h2>

                                <p>
                                    Rule-based and machine-learning analysis
                                    of the latest telemetry.
                                </p>
                            </div>
                        </div>

                        <div className="telemetry-diagnostic-grid">
                            <div className="telemetry-diagnostic-main">
                                <span>Final Diagnosis</span>

                                <strong>
                                    {formatLabel(diagnosis)}
                                </strong>

                                <p>
                                    SolarAI combines telemetry validation,
                                    diagnostic rules and ML prediction to
                                    determine the system condition.
                                </p>
                            </div>

                            <div className="telemetry-ai-details">
                                <div>
                                    <span>Rule Diagnosis</span>

                                    <strong>
                                        {formatLabel(
                                            telemetry.fault_type
                                        )}
                                    </strong>
                                </div>

                                <div>
                                    <span>Fault Severity</span>

                                    <strong>
                                        {formatLabel(
                                            telemetry.fault_severity
                                        )}
                                    </strong>
                                </div>

                                <div>
                                    <span>ML Prediction</span>

                                    <strong>
                                        {telemetry.ml_prediction_available ===
                                            0
                                            ? "Unavailable"
                                            : formatLabel(
                                                telemetry.ml_prediction
                                            )}
                                    </strong>
                                </div>

                                <div>
                                    <span>ML Confidence</span>

                                    <strong>
                                        {telemetry.ml_prediction_available ===
                                            0
                                            ? "—"
                                            : confidencePercentage(
                                                telemetry.ml_confidence
                                            )}
                                    </strong>
                                </div>

                                <div>
                                    <span>Prediction Agreement</span>

                                    <strong>
                                        {formatLabel(
                                            telemetry.prediction_agreement
                                        )}
                                    </strong>
                                </div>

                                <div>
                                    <span>Error Code</span>

                                    <strong>
                                        {telemetry.error_code || "None"}
                                    </strong>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* DATA QUALITY */}

                    <section className="telemetry-section">
                        <div className="telemetry-section-heading">
                            <div>
                                <h2>Telemetry Quality</h2>

                                <p>
                                    Check whether the incoming sensor data is
                                    complete enough for reliable analysis.
                                </p>
                            </div>
                        </div>

                        <div className="telemetry-quality-layout">
                            <div className="quality-score-card">
                                <span>Data Quality Score</span>

                                <strong>
                                    {displayValue(
                                        telemetry.data_quality_score,
                                        "%"
                                    )}
                                </strong>

                                <div className="quality-progress">
                                    <div
                                        className="quality-progress-bar"
                                        style={{
                                            width: `${Math.min(
                                                100,
                                                Math.max(
                                                    0,
                                                    Number(
                                                        telemetry.data_quality_score ||
                                                        0
                                                    )
                                                )
                                            )}%`,
                                        }}
                                    />
                                </div>
                            </div>

                            <div className="quality-information">
                                <div>
                                    <span>Missing Fields</span>

                                    <strong>
                                        {telemetry.missing_fields ||
                                            "None"}
                                    </strong>
                                </div>

                                <div>
                                    <span>Review Status</span>

                                    <strong>
                                        {needsReview
                                            ? "Needs technician review"
                                            : "No review required"}
                                    </strong>
                                </div>

                                <div>
                                    <span>Telemetry ID</span>

                                    <strong>
                                        #{telemetry.id}
                                    </strong>
                                </div>
                            </div>
                        </div>
                    </section>
                </>
            )}
        </div>
    );
}

export default Telemetry;