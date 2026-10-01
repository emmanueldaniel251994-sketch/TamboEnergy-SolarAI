import { useEffect, useState } from "react";
import {
    ResponsiveContainer,
    LineChart,
    Line,
    CartesianGrid,
    XAxis,
    YAxis,
    Tooltip,
    Legend,
    BarChart,
    Bar,
} from "recharts";

const API_BASE_URL = "http://127.0.0.1:8000";

function Analytics({ token }) {
    const [solarSystems, setSolarSystems] = useState([]);
    const [selectedSystemId, setSelectedSystemId] = useState("");
    const [analyticsData, setAnalyticsData] = useState(null);

    const [loadingSystems, setLoadingSystems] = useState(true);
    const [loadingAnalytics, setLoadingAnalytics] = useState(false);

    const [error, setError] = useState("");

    // ============================================================
    // LOAD SOLAR SYSTEMS
    // ============================================================

    const loadSolarSystems = async () => {
        setLoadingSystems(true);
        setError("");

        try {
            const response = await fetch(
                `${API_BASE_URL}/solar-systems/`,
                {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
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
                    const currentExists = systems.some(
                        (system) =>
                            String(system.id) === String(current)
                    );

                    if (current && currentExists) {
                        return current;
                    }

                    return String(systems[0].id);
                });
            } else {
                setSelectedSystemId("");
                setAnalyticsData(null);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoadingSystems(false);
        }
    };

    // ============================================================
    // LOAD ANALYTICS
    // ============================================================

    const loadAnalytics = async (systemId) => {
        if (!systemId) {
            return;
        }

        setLoadingAnalytics(true);
        setError("");

        try {
            const response = await fetch(
                `${API_BASE_URL}/dashboard/analytics/${systemId}`,
                {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Unable to load analytics."
                );
            }

            setAnalyticsData(data);
        } catch (err) {
            setAnalyticsData(null);
            setError(err.message);
        } finally {
            setLoadingAnalytics(false);
        }
    };

    useEffect(() => {
        loadSolarSystems();
    }, []);

    useEffect(() => {
        if (selectedSystemId) {
            loadAnalytics(selectedSystemId);
        }
    }, [selectedSystemId]);

    // ============================================================
    // HELPERS
    // ============================================================

    const formatNumber = (value, decimals = 1) => {
        if (
            value === null ||
            value === undefined ||
            Number.isNaN(Number(value))
        ) {
            return "—";
        }

        return Number(value).toFixed(decimals);
    };

    const formatChartTime = (timestamp) => {
        if (!timestamp) {
            return "—";
        }

        const date = new Date(timestamp);

        if (Number.isNaN(date.getTime())) {
            return timestamp;
        }

        return date.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    const formatFullDate = (timestamp) => {
        if (!timestamp) {
            return "—";
        }

        const date = new Date(timestamp);

        if (Number.isNaN(date.getTime())) {
            return timestamp;
        }

        return date.toLocaleString();
    };

    // ============================================================
    // CHART DATA
    // ============================================================

    const chartData =
        analyticsData?.data?.map((record) => ({
            ...record,
            chartTime: formatChartTime(record.timestamp),

            pv_power:
                record.pv_power == null
                    ? null
                    : Number(record.pv_power),

            load_power:
                record.load_power == null
                    ? null
                    : Number(record.load_power),

            battery_soc:
                record.battery_soc == null
                    ? null
                    : Number(record.battery_soc),

            temperature:
                record.temperature == null
                    ? null
                    : Number(record.temperature),
        })) || [];

    const analytics = analyticsData?.analytics;

    return (
        <div className="analytics-page">

            {/* PAGE HEADER */}

            <div className="page-header">
                <div>
                    <h1>Analytics</h1>

                    <p>
                        Monitor solar production, load demand,
                        battery performance and system health.
                    </p>
                </div>

                <button
                    type="button"
                    className="secondary-button"
                    disabled={
                        !selectedSystemId ||
                        loadingAnalytics
                    }
                    onClick={() =>
                        loadAnalytics(selectedSystemId)
                    }
                >
                    {loadingAnalytics
                        ? "Refreshing..."
                        : "Refresh Analytics"}
                </button>
            </div>

            {/* ERROR */}

            {error && (
                <div className="diagnostic-message">
                    {error}
                </div>
            )}

            {/* SYSTEM SELECTOR */}

            <div className="analytics-selector-card">
                <div className="analytics-selector">

                    <div className="analytics-selector-field">
                        <label htmlFor="analytics-system">
                            Solar System
                        </label>

                        <select
                            id="analytics-system"
                            value={selectedSystemId}
                            disabled={loadingSystems}
                            onChange={(event) => {
                                setSelectedSystemId(
                                    event.target.value
                                );
                                setAnalyticsData(null);
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

                    {analyticsData && (
                        <div className="analytics-record-count">
                            <span>Telemetry Records</span>
                            <strong>
                                {analyticsData.record_count}
                            </strong>
                        </div>
                    )}

                </div>
            </div>

            {/* LOADING */}

            {loadingAnalytics && (
                <div className="diagnostic-empty-state">
                    <h3>Loading analytics...</h3>

                    <p>
                        SolarAI is processing the system
                        telemetry data.
                    </p>
                </div>
            )}

            {/* NO SYSTEMS */}

            {!loadingSystems &&
                solarSystems.length === 0 && (
                    <div className="diagnostic-empty-state">
                        <h3>No solar systems available</h3>

                        <p>
                            Register a solar system before
                            viewing analytics.
                        </p>
                    </div>
                )}

            {/* NO TELEMETRY */}

            {!loadingAnalytics &&
                analyticsData &&
                analyticsData.record_count === 0 && (
                    <div className="diagnostic-empty-state">
                        <h3>No analytics data yet</h3>

                        <p>
                            Solar System #
                            {analyticsData.solar_system_id} has
                            no telemetry records available.
                        </p>
                    </div>
                )}

            {/* MAIN ANALYTICS */}

            {!loadingAnalytics &&
                analyticsData &&
                analyticsData.record_count > 0 &&
                analytics && (
                    <>

                        {/* SUMMARY */}

                        <section className="analytics-section">
                            <div className="analytics-section-heading">
                                <div>
                                    <h2>Performance Overview</h2>

                                    <p>
                                        Solar System #
                                        {analyticsData.solar_system_id}
                                    </p>
                                </div>
                            </div>

                            <div className="analytics-summary-grid">

                                <div className="analytics-metric-card">
                                    <span>Average PV Power</span>
                                    <strong>
                                        {formatNumber(
                                            analytics.average_pv_power
                                        )} W
                                    </strong>
                                </div>

                                <div className="analytics-metric-card">
                                    <span>Peak PV Power</span>
                                    <strong>
                                        {formatNumber(
                                            analytics.peak_pv_power
                                        )} W
                                    </strong>
                                </div>

                                <div className="analytics-metric-card">
                                    <span>Average Load</span>
                                    <strong>
                                        {formatNumber(
                                            analytics.average_load_power
                                        )} W
                                    </strong>
                                </div>

                                <div className="analytics-metric-card">
                                    <span>Peak Load</span>
                                    <strong>
                                        {formatNumber(
                                            analytics.peak_load_power
                                        )} W
                                    </strong>
                                </div>

                                <div className="analytics-metric-card">
                                    <span>Average Battery SOC</span>
                                    <strong>
                                        {formatNumber(
                                            analytics.average_battery_soc
                                        )}%
                                    </strong>
                                </div>

                                <div className="analytics-metric-card">
                                    <span>Minimum Battery SOC</span>
                                    <strong>
                                        {formatNumber(
                                            analytics.minimum_battery_soc
                                        )}%
                                    </strong>
                                </div>

                                <div className="analytics-metric-card">
                                    <span>Average Temperature</span>
                                    <strong>
                                        {formatNumber(
                                            analytics.average_temperature
                                        )} °C
                                    </strong>
                                </div>

                                <div className="analytics-metric-card">
                                    <span>Maximum Temperature</span>
                                    <strong>
                                        {formatNumber(
                                            analytics.maximum_temperature
                                        )} °C
                                    </strong>
                                </div>

                            </div>
                        </section>

                        {/* PV VS LOAD CHART */}

                        <section className="analytics-section">
                            <div className="analytics-section-heading">
                                <div>
                                    <h2>Solar Production vs Load</h2>

                                    <p>
                                        Compare PV generation with
                                        energy demand over time.
                                    </p>
                                </div>
                            </div>

                            <div className="analytics-chart">
                                <ResponsiveContainer
                                    width="100%"
                                    height={340}
                                >
                                    <LineChart data={chartData}>
                                        <CartesianGrid
                                            strokeDasharray="3 3"
                                        />

                                        <XAxis dataKey="chartTime" />

                                        <YAxis />

                                        <Tooltip />

                                        <Legend />

                                        <Line
                                            type="monotone"
                                            dataKey="pv_power"
                                            name="PV Power (W)"
                                            stroke="#08745c"
                                            strokeWidth={3}
                                            connectNulls
                                        />

                                        <Line
                                            type="monotone"
                                            dataKey="load_power"
                                            name="Load Power (W)"
                                            stroke="#d59c18"
                                            strokeWidth={3}
                                            connectNulls
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </section>

                        {/* BATTERY CHART */}

                        <section className="analytics-section">
                            <div className="analytics-section-heading">
                                <div>
                                    <h2>Battery State of Charge</h2>

                                    <p>
                                        Battery SOC across available
                                        telemetry readings.
                                    </p>
                                </div>
                            </div>

                            <div className="analytics-chart">
                                <ResponsiveContainer
                                    width="100%"
                                    height={300}
                                >
                                    <LineChart data={chartData}>
                                        <CartesianGrid
                                            strokeDasharray="3 3"
                                        />

                                        <XAxis dataKey="chartTime" />

                                        <YAxis domain={[0, 100]} />

                                        <Tooltip />

                                        <Legend />

                                        <Line
                                            type="monotone"
                                            dataKey="battery_soc"
                                            name="Battery SOC (%)"
                                            stroke="#2f7d68"
                                            strokeWidth={3}
                                            connectNulls
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>

                            <div className="battery-range">
                                <div>
                                    <span>Minimum SOC</span>
                                    <strong>
                                        {formatNumber(
                                            analytics.minimum_battery_soc
                                        )}%
                                    </strong>
                                </div>

                                <div>
                                    <span>Average SOC</span>
                                    <strong>
                                        {formatNumber(
                                            analytics.average_battery_soc
                                        )}%
                                    </strong>
                                </div>

                                <div>
                                    <span>Maximum SOC</span>
                                    <strong>
                                        {formatNumber(
                                            analytics.maximum_battery_soc
                                        )}%
                                    </strong>
                                </div>
                            </div>
                        </section>

                        {/* TEMPERATURE */}

                        <section className="analytics-section">
                            <div className="analytics-section-heading">
                                <div>
                                    <h2>Temperature Trend</h2>

                                    <p>
                                        Track system operating
                                        temperature over time.
                                    </p>
                                </div>
                            </div>

                            <div className="analytics-chart">
                                <ResponsiveContainer
                                    width="100%"
                                    height={300}
                                >
                                    <LineChart data={chartData}>
                                        <CartesianGrid
                                            strokeDasharray="3 3"
                                        />

                                        <XAxis dataKey="chartTime" />

                                        <YAxis />

                                        <Tooltip />

                                        <Legend />

                                        <Line
                                            type="monotone"
                                            dataKey="temperature"
                                            name="Temperature (°C)"
                                            stroke="#c96a3d"
                                            strokeWidth={3}
                                            connectNulls
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </section>

                        {/* SYSTEM CONDITION */}

                        <section className="analytics-section">
                            <div className="analytics-section-heading">
                                <div>
                                    <h2>System Condition</h2>

                                    <p>
                                        Diagnostic classification of
                                        telemetry records.
                                    </p>
                                </div>
                            </div>

                            <div className="analytics-condition-layout">

                                <div className="analytics-chart">
                                    <ResponsiveContainer
                                        width="100%"
                                        height={280}
                                    >
                                        <BarChart
                                            data={[
                                                {
                                                    category: "Normal",
                                                    count:
                                                        analytics.normal_count,
                                                },
                                                {
                                                    category: "Warnings",
                                                    count:
                                                        analytics.warning_count,
                                                },
                                                {
                                                    category: "Faults",
                                                    count:
                                                        analytics.fault_count,
                                                },
                                                {
                                                    category: "Review",
                                                    count:
                                                        analytics.needs_review_count,
                                                },
                                            ]}
                                        >
                                            <CartesianGrid
                                                strokeDasharray="3 3"
                                            />

                                            <XAxis dataKey="category" />

                                            <YAxis
                                                allowDecimals={false}
                                            />

                                            <Tooltip />

                                            <Bar
                                                dataKey="count"
                                                name="Records"
                                                fill="#08745c"
                                                radius={[6, 6, 0, 0]}
                                            />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>

                                <div className="condition-summary">

                                    <div>
                                        <span>Normal</span>
                                        <strong>
                                            {analytics.normal_count}
                                        </strong>
                                    </div>

                                    <div>
                                        <span>Warnings</span>
                                        <strong>
                                            {analytics.warning_count}
                                        </strong>
                                    </div>

                                    <div>
                                        <span>Faults</span>
                                        <strong>
                                            {analytics.fault_count}
                                        </strong>
                                    </div>

                                    <div>
                                        <span>Needs Review</span>
                                        <strong>
                                            {analytics.needs_review_count}
                                        </strong>
                                    </div>

                                </div>
                            </div>
                        </section>

                        {/* TELEMETRY HISTORY */}

                        <section className="analytics-section">
                            <div className="analytics-section-heading">
                                <div>
                                    <h2>Recent Telemetry Analysis</h2>

                                    <p>
                                        AI diagnostic results from
                                        available telemetry.
                                    </p>
                                </div>
                            </div>

                            <div className="table-wrapper">
                                <table className="data-table">

                                    <thead>
                                        <tr>
                                            <th>Telemetry</th>
                                            <th>Time</th>
                                            <th>PV</th>
                                            <th>Load</th>
                                            <th>Battery</th>
                                            <th>Temperature</th>
                                            <th>Diagnosis</th>
                                            <th>ML Confidence</th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {[...chartData]
                                            .reverse()
                                            .map((record) => (
                                                <tr
                                                    key={record.telemetry_id}
                                                >
                                                    <td>
                                                        #{record.telemetry_id}
                                                    </td>

                                                    <td>
                                                        {formatFullDate(
                                                            record.timestamp
                                                        )}
                                                    </td>

                                                    <td>
                                                        {record.pv_power ?? "—"} W
                                                    </td>

                                                    <td>
                                                        {record.load_power ?? "—"} W
                                                    </td>

                                                    <td>
                                                        {record.battery_soc ?? "—"}%
                                                    </td>

                                                    <td>
                                                        {record.temperature ?? "—"} °C
                                                    </td>

                                                    <td>
                                                        <span className="table-status">
                                                            {record.final_diagnosis ||
                                                                record.fault_type ||
                                                                record.status ||
                                                                "Unknown"}
                                                        </span>
                                                    </td>

                                                    <td>
                                                        {record.ml_confidence != null
                                                            ? `${(
                                                                Number(
                                                                    record.ml_confidence
                                                                ) * 100
                                                            ).toFixed(1)}%`
                                                            : "—"}
                                                    </td>
                                                </tr>
                                            ))}
                                    </tbody>

                                </table>
                            </div>
                        </section>

                    </>
                )}
        </div>
    );
}

export default Analytics;