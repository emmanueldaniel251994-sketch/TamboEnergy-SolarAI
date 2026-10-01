import { API_BASE_URL } from "../config";
import { useCallback, useEffect, useState } from "react";

function Alerts({ token }) {
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [actionId, setActionId] = useState(null);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    // =========================================================
    // LOAD ALERTS
    // =========================================================

    const loadAlerts = useCallback(async () => {
        try {
            setLoading(true);
            setError("");

            const response = await fetch(
                `${API_BASE_URL}/alerts/`,
                {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Unable to load alerts."
                );
            }

            setAlerts(Array.isArray(data) ? data : []);
        } catch (error) {
            setError(error.message);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        loadAlerts();
    }, [loadAlerts]);

    // =========================================================
    // ACKNOWLEDGE ALERT
    // =========================================================

    const handleAcknowledge = async (alert) => {
        setActionId(alert.id);
        setError("");
        setSuccess("");

        try {
            const response = await fetch(
                `${API_BASE_URL}/alerts/${alert.id}/acknowledge`,
                {
                    method: "PUT",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            let data = {};

            try {
                data = await response.json();
            } catch {
                // Response may not contain JSON
            }

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                    "Unable to acknowledge alert."
                );
            }

            setSuccess(
                `Alert #${alert.id} acknowledged successfully.`
            );

            await loadAlerts();
        } catch (error) {
            setError(error.message);
        } finally {
            setActionId(null);
        }
    };

    // =========================================================
    // RESOLVE ALERT
    // =========================================================

    const handleResolve = async (alert) => {
        const confirmed = window.confirm(
            `Resolve alert #${alert.id}?\n\n${alert.title}`
        );

        if (!confirmed) {
            return;
        }

        setActionId(alert.id);
        setError("");
        setSuccess("");

        try {
            const response = await fetch(
                `${API_BASE_URL}/alerts/${alert.id}/resolve`,
                {
                    method: "PUT",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            let data = {};

            try {
                data = await response.json();
            } catch {
                // Response may not contain JSON
            }

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                    "Unable to resolve alert."
                );
            }

            setSuccess(
                `Alert #${alert.id} resolved successfully.`
            );

            await loadAlerts();
        } catch (error) {
            setError(error.message);
        } finally {
            setActionId(null);
        }
    };

    // =========================================================
    // DELETE ALERT
    // Admin Only
    // =========================================================

    const handleDelete = async (alert) => {
        const confirmed = window.confirm(
            `Permanently delete alert #${alert.id}?\n\n` +
            `${alert.title}\n\n` +
            "This action cannot be undone."
        );

        if (!confirmed) {
            return;
        }

        setActionId(alert.id);
        setError("");
        setSuccess("");

        try {
            const response = await fetch(
                `${API_BASE_URL}/alerts/${alert.id}`,
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
                // Response may not contain JSON
            }

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                    "Unable to delete alert."
                );
            }

            setSuccess(
                `Alert #${alert.id} deleted successfully.`
            );

            await loadAlerts();
        } catch (error) {
            setError(error.message);
        } finally {
            setActionId(null);
        }
    };

    // =========================================================
    // FORMAT DATE
    // =========================================================

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

    // =========================================================
    // SUMMARY COUNTS
    // =========================================================

    const openAlerts = alerts.filter(
        (alert) => alert.status === "open"
    ).length;

    const acknowledgedAlerts = alerts.filter(
        (alert) => alert.status === "acknowledged"
    ).length;

    const resolvedAlerts = alerts.filter(
        (alert) => alert.status === "resolved"
    ).length;

    const criticalAlerts = alerts.filter(
        (alert) =>
            alert.severity?.toLowerCase() === "critical"
    ).length;

    // =========================================================
    // PAGE
    // =========================================================

    return (
        <div className="page-content">

            {/* HEADER */}

            <div className="page-header">
                <div>
                    <p className="dashboard-label">
                        SOLAR SYSTEM MONITORING
                    </p>

                    <h1>Alerts</h1>

                    <p>
                        Monitor warnings, faults and system
                        conditions detected by TamboEnergy SolarAI.
                    </p>
                </div>

                <button
                    type="button"
                    className="secondary-button"
                    onClick={loadAlerts}
                    disabled={loading}
                >
                    {loading ? "Refreshing..." : "Refresh"}
                </button>
            </div>

            {/* ERROR */}

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            {/* SUCCESS */}

            {success && (
                <div className="success-message">
                    {success}
                </div>
            )}

            {/* SUMMARY */}

            <div className="alert-summary-grid">

                <div className="alert-summary-card">
                    <span>Total Alerts</span>
                    <strong>{alerts.length}</strong>
                </div>

                <div className="alert-summary-card">
                    <span>Open</span>
                    <strong>{openAlerts}</strong>
                </div>

                <div className="alert-summary-card">
                    <span>Acknowledged</span>
                    <strong>{acknowledgedAlerts}</strong>
                </div>

                <div className="alert-summary-card">
                    <span>Resolved</span>
                    <strong>{resolvedAlerts}</strong>
                </div>

                <div className="alert-summary-card">
                    <span>Critical</span>
                    <strong>{criticalAlerts}</strong>
                </div>

            </div>

            {/* ALERTS */}

            <div className="alerts-page-list">

                {loading ? (

                    <div className="page-loading">
                        Loading alerts...
                    </div>

                ) : alerts.length === 0 ? (

                    <div className="empty-state">
                        No alerts are currently available.
                    </div>

                ) : (

                    alerts.map((alert) => (

                        <div
                            className={`alert-page-card severity-${
                                alert.severity?.toLowerCase() ||
                                "unknown"
                            }`}
                            key={alert.id}
                        >

                            {/* ALERT HEADER */}

                            <div className="alert-page-header">

                                <div>

                                    <div className="alert-page-badges">

                                        <span
                                            className={`alert-severity ${
                                                alert.severity || ""
                                            }`}
                                        >
                                            {alert.severity || "unknown"}
                                        </span>

                                        <span
                                            className={`alert-page-status status-${
                                                alert.status || "unknown"
                                            }`}
                                        >
                                            {alert.status || "unknown"}
                                        </span>

                                        {alert.needs_review === 1 && (
                                            <span className="review-badge">
                                                Needs Review
                                            </span>
                                        )}

                                    </div>

                                    <h3>{alert.title}</h3>

                                </div>

                                <strong className="alert-number">
                                    #{alert.id}
                                </strong>

                            </div>

                            {/* MESSAGE */}

                            <p className="alert-page-message">
                                {alert.message}
                            </p>

                            {/* DETAILS */}

                            <div className="alert-details-grid">

                                <div>
                                    <span>Solar System</span>
                                    <strong>
                                        #{alert.solar_system_id}
                                    </strong>
                                </div>

                                <div>
                                    <span>Telemetry</span>
                                    <strong>
                                        {alert.telemetry_id
                                            ? `#${alert.telemetry_id}`
                                            : "—"}
                                    </strong>
                                </div>

                                <div>
                                    <span>Alert Type</span>
                                    <strong>
                                        {alert.alert_type || "—"}
                                    </strong>
                                </div>

                                <div>
                                    <span>Created</span>
                                    <strong>
                                        {formatDate(alert.created_at)}
                                    </strong>
                                </div>

                            </div>

                            {/* LIFECYCLE */}

                            {(alert.acknowledged_at ||
                                alert.resolved_at) && (

                                <div className="alert-timeline">

                                    {alert.acknowledged_at && (
                                        <span>
                                            Acknowledged:{" "}
                                            {formatDate(
                                                alert.acknowledged_at
                                            )}
                                        </span>
                                    )}

                                    {alert.resolved_at && (
                                        <span>
                                            Resolved:{" "}
                                            {formatDate(
                                                alert.resolved_at
                                            )}
                                        </span>
                                    )}

                                </div>

                            )}

                            {/* ACTIONS */}

                            <div className="alert-page-actions">

                                {alert.status === "open" && (

                                    <button
                                        type="button"
                                        className="acknowledge-button"
                                        disabled={
                                            actionId === alert.id
                                        }
                                        onClick={() =>
                                            handleAcknowledge(alert)
                                        }
                                    >
                                        {actionId === alert.id
                                            ? "Processing..."
                                            : "Acknowledge"}
                                    </button>

                                )}

                                {alert.status !== "resolved" && (

                                    <button
                                        type="button"
                                        className="resolve-button"
                                        disabled={
                                            actionId === alert.id
                                        }
                                        onClick={() =>
                                            handleResolve(alert)
                                        }
                                    >
                                        {actionId === alert.id
                                            ? "Processing..."
                                            : "Resolve"}
                                    </button>

                                )}

                                {/* DELETE */}

                                <button
                                    type="button"
                                    className="delete-button"
                                    disabled={
                                        actionId === alert.id
                                    }
                                    onClick={() =>
                                        handleDelete(alert)
                                    }
                                >
                                    {actionId === alert.id
                                        ? "Processing..."
                                        : "Delete"}
                                </button>

                                {alert.status === "resolved" && (
                                    <span className="resolved-label">
                                        ✓ Resolved
                                    </span>
                                )}

                            </div>

                        </div>

                    ))

                )}

            </div>

        </div>
    );
}

export default Alerts;