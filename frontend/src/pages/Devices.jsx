import { API_BASE_URL } from "../config";
import { useCallback, useEffect, useMemo, useState } from "react";

const EMPTY_FORM = {
    solar_system_id: "",
    device_name: "",
    device_type: "monitoring_gateway",
    manufacturer: "TamboEnergy",
    model: "",
    serial_number: "",
};

function Devices({ token, currentUser }) {
    const [devices, setDevices] = useState([]);
    const [systems, setSystems] = useState([]);
    const [formData, setFormData] = useState(EMPTY_FORM);
    const [showForm, setShowForm] = useState(false);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [actionId, setActionId] = useState(null);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [issuedApiKey, setIssuedApiKey] = useState(null);

    const role = currentUser?.role || "";
    const canManage = role === "admin" || role === "technician";
    const isAdmin = role === "admin";

    const authHeaders = useMemo(
        () => ({ Authorization: `Bearer ${token}` }),
        [token]
    );

    const loadData = useCallback(async () => {
        setLoading(true);
        setError("");

        try {
            const [deviceResponse, systemResponse] = await Promise.all([
                fetch(`${API_BASE_URL}/devices/`, {
                    headers: authHeaders,
                }),
                fetch(`${API_BASE_URL}/solar-systems/`, {
                    headers: authHeaders,
                }),
            ]);

            const deviceData = await deviceResponse.json();
            const systemData = await systemResponse.json();

            if (!deviceResponse.ok) {
                throw new Error(
                    deviceData.detail || "Unable to load devices."
                );
            }

            if (!systemResponse.ok) {
                throw new Error(
                    systemData.detail || "Unable to load solar systems."
                );
            }

            setDevices(Array.isArray(deviceData) ? deviceData : []);
            setSystems(Array.isArray(systemData) ? systemData : []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [authHeaders]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleChange = (event) => {
        const { name, value } = event.target;
        setFormData((current) => ({ ...current, [name]: value }));
    };

    const registerDevice = async (event) => {
        event.preventDefault();
        setSaving(true);
        setError("");
        setSuccess("");
        setIssuedApiKey(null);

        try {
            const payload = {
                solar_system_id: Number(formData.solar_system_id),
                device_name: formData.device_name.trim(),
                device_type:
                    formData.device_type.trim() || "monitoring_gateway",
                manufacturer: formData.manufacturer.trim() || null,
                model: formData.model.trim() || null,
                serial_number: formData.serial_number.trim() || null,
            };

            if (!payload.solar_system_id) {
                throw new Error("Please select a solar system.");
            }

            if (payload.device_name.length < 2) {
                throw new Error("Please enter a device name.");
            }

            const response = await fetch(`${API_BASE_URL}/devices/`, {
                method: "POST",
                headers: {
                    ...authHeaders,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Unable to register device."
                );
            }

            setIssuedApiKey({
                deviceId: data.id,
                deviceName: data.device_name,
                apiKey: data.api_key,
            });
            setSuccess(`Device #${data.id} registered successfully.`);
            setFormData(EMPTY_FORM);
            setShowForm(false);
            await loadData();
        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    };

    const updateActiveState = async (device) => {
        setActionId(device.id);
        setError("");
        setSuccess("");

        try {
            const response = await fetch(
                `${API_BASE_URL}/devices/${device.id}`,
                {
                    method: "PUT",
                    headers: {
                        ...authHeaders,
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        is_active: !device.is_active,
                    }),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Unable to update device."
                );
            }

            setSuccess(
                `Device #${device.id} ${
                    data.is_active ? "activated" : "deactivated"
                }.`
            );
            await loadData();
        } catch (err) {
            setError(err.message);
        } finally {
            setActionId(null);
        }
    };

    const rotateApiKey = async (device) => {
        const confirmed = window.confirm(
            `Rotate the API key for ${device.device_name}?\n\n` +
                "The current device key will stop working immediately."
        );

        if (!confirmed) {
            return;
        }

        setActionId(device.id);
        setError("");
        setSuccess("");
        setIssuedApiKey(null);

        try {
            const response = await fetch(
                `${API_BASE_URL}/devices/${device.id}/rotate-api-key`,
                {
                    method: "POST",
                    headers: authHeaders,
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Unable to rotate API key."
                );
            }

            setIssuedApiKey({
                deviceId: data.id,
                deviceName: data.device_name,
                apiKey: data.api_key,
            });
            setSuccess(`API key rotated for device #${data.id}.`);
            await loadData();
        } catch (err) {
            setError(err.message);
        } finally {
            setActionId(null);
        }
    };

    const deleteDevice = async (device) => {
        const confirmed = window.confirm(
            `Delete device #${device.id} — ${device.device_name}?\n\n` +
                "Stored telemetry will be preserved, but the device will no longer be able to report."
        );

        if (!confirmed) {
            return;
        }

        setActionId(device.id);
        setError("");
        setSuccess("");

        try {
            const response = await fetch(
                `${API_BASE_URL}/devices/${device.id}`,
                {
                    method: "DELETE",
                    headers: authHeaders,
                }
            );

            let data = {};
            try {
                data = await response.json();
            } catch {
                // no-op
            }

            if (!response.ok) {
                throw new Error(
                    data.detail || "Unable to delete device."
                );
            }

            setSuccess(`Device #${device.id} deleted.`);
            await loadData();
        } catch (err) {
            setError(err.message);
        } finally {
            setActionId(null);
        }
    };

    const copyApiKey = async () => {
        if (!issuedApiKey?.apiKey) {
            return;
        }

        try {
            await navigator.clipboard.writeText(issuedApiKey.apiKey);
            setSuccess("Device API key copied to the clipboard.");
        } catch {
            setError(
                "The browser could not copy the key automatically. Select and copy it manually."
            );
        }
    };

    const formatDate = (value) => {
        if (!value) {
            return "Never";
        }

        const date = new Date(value);
        return Number.isNaN(date.getTime())
            ? value
            : date.toLocaleString();
    };

    const systemLabel = (systemId) => {
        const system = systems.find(
            (item) => Number(item.id) === Number(systemId)
        );

        if (!system) {
            return `System #${systemId}`;
        }

        return `System #${system.id}${
            system.location ? ` — ${system.location}` : ""
        }`;
    };

    const activeCount = devices.filter((device) => device.is_active).length;
    const reportedCount = devices.filter((device) => device.last_seen).length;

    return (
        <div className="page-content devices-page">
            <div className="page-header">
                <div>
                    <p className="dashboard-label">DEVICE FLEET</p>
                    <h1>Devices</h1>
                    <p>
                        Register monitoring gateways, control device access and
                        track the source of SolarAI telemetry.
                    </p>
                </div>

                <div className="device-header-actions">
                    <button
                        type="button"
                        className="secondary-button"
                        onClick={loadData}
                        disabled={loading}
                    >
                        {loading ? "Refreshing..." : "Refresh"}
                    </button>

                    {canManage && (
                        <button
                            type="button"
                            className="primary-action-button"
                            onClick={() => setShowForm((current) => !current)}
                        >
                            {showForm ? "Close Form" : "Register Device"}
                        </button>
                    )}
                </div>
            </div>

            {error && <div className="error-message">{error}</div>}
            {success && <div className="success-message">{success}</div>}

            {issuedApiKey && (
                <section className="device-key-panel">
                    <div>
                        <span>ONE-TIME DEVICE API KEY</span>
                        <h3>{issuedApiKey.deviceName}</h3>
                        <p>
                            Save this key now. SolarAI stores only its hash and
                            will not show this exact key again.
                        </p>
                    </div>

                    <code>{issuedApiKey.apiKey}</code>

                    <div className="device-key-actions">
                        <button type="button" onClick={copyApiKey}>
                            Copy Key
                        </button>
                        <button
                            type="button"
                            className="secondary-button"
                            onClick={() => setIssuedApiKey(null)}
                        >
                            I Have Saved It
                        </button>
                    </div>
                </section>
            )}

            <div className="device-summary-grid">
                <div className="device-summary-card">
                    <span>Total Devices</span>
                    <strong>{devices.length}</strong>
                </div>
                <div className="device-summary-card">
                    <span>Active Credentials</span>
                    <strong>{activeCount}</strong>
                </div>
                <div className="device-summary-card">
                    <span>Have Reported</span>
                    <strong>{reportedCount}</strong>
                </div>
            </div>

            {showForm && canManage && (
                <section className="device-form-card">
                    <div className="telemetry-section-heading">
                        <div>
                            <h2>Register Monitoring Device</h2>
                            <p>
                                The API key is generated by the backend and is
                                displayed only once after registration.
                            </p>
                        </div>
                    </div>

                    <form className="device-form-grid" onSubmit={registerDevice}>
                        <label>
                            Solar System
                            <select
                                name="solar_system_id"
                                value={formData.solar_system_id}
                                onChange={handleChange}
                                required
                            >
                                <option value="">Select solar system</option>
                                {systems.map((system) => (
                                    <option key={system.id} value={system.id}>
                                        {systemLabel(system.id)}
                                    </option>
                                ))}
                            </select>
                        </label>

                        <label>
                            Device Name
                            <input
                                name="device_name"
                                value={formData.device_name}
                                onChange={handleChange}
                                placeholder="TamboEnergy Site Gateway"
                                required
                            />
                        </label>

                        <label>
                            Device Type
                            <input
                                name="device_type"
                                value={formData.device_type}
                                onChange={handleChange}
                                required
                            />
                        </label>

                        <label>
                            Manufacturer
                            <input
                                name="manufacturer"
                                value={formData.manufacturer}
                                onChange={handleChange}
                            />
                        </label>

                        <label>
                            Model
                            <input
                                name="model"
                                value={formData.model}
                                onChange={handleChange}
                                placeholder="SolarAI Gateway Prototype"
                            />
                        </label>

                        <label>
                            Serial Number
                            <input
                                name="serial_number"
                                value={formData.serial_number}
                                onChange={handleChange}
                                placeholder="TAMBO-0001"
                            />
                        </label>

                        <div className="device-form-actions">
                            <button
                                type="submit"
                                className="primary-action-button"
                                disabled={saving}
                            >
                                {saving ? "Registering..." : "Register Device"}
                            </button>
                        </div>
                    </form>
                </section>
            )}

            {loading ? (
                <div className="page-loading">Loading devices...</div>
            ) : devices.length === 0 ? (
                <div className="empty-state">
                    No monitoring devices have been registered yet.
                </div>
            ) : (
                <div className="device-grid">
                    {devices.map((device) => (
                        <article className="device-card" key={device.id}>
                            <div className="device-card-header">
                                <div>
                                    <span className="device-id">DEVICE #{device.id}</span>
                                    <h3>{device.device_name}</h3>
                                    <p>{systemLabel(device.solar_system_id)}</p>
                                </div>
                                <span
                                    className={`device-state ${
                                        device.is_active ? "active" : "inactive"
                                    }`}
                                >
                                    {device.is_active ? "Active" : "Inactive"}
                                </span>
                            </div>

                            <div className="device-detail-grid">
                                <div>
                                    <span>Type</span>
                                    <strong>{device.device_type || "—"}</strong>
                                </div>
                                <div>
                                    <span>Manufacturer</span>
                                    <strong>{device.manufacturer || "—"}</strong>
                                </div>
                                <div>
                                    <span>Model</span>
                                    <strong>{device.model || "—"}</strong>
                                </div>
                                <div>
                                    <span>Serial</span>
                                    <strong>{device.serial_number || "—"}</strong>
                                </div>
                                <div>
                                    <span>Last Seen</span>
                                    <strong>{formatDate(device.last_seen)}</strong>
                                </div>
                                <div>
                                    <span>Registered</span>
                                    <strong>{formatDate(device.created_at)}</strong>
                                </div>
                            </div>

                            {canManage && (
                                <div className="device-card-actions">
                                    <button
                                        type="button"
                                        className="secondary-button"
                                        disabled={actionId === device.id}
                                        onClick={() => updateActiveState(device)}
                                    >
                                        {device.is_active ? "Deactivate" : "Activate"}
                                    </button>

                                    {isAdmin && (
                                        <>
                                            <button
                                                type="button"
                                                className="secondary-button"
                                                disabled={actionId === device.id}
                                                onClick={() => rotateApiKey(device)}
                                            >
                                                Rotate API Key
                                            </button>
                                            <button
                                                type="button"
                                                className="delete-button"
                                                disabled={actionId === device.id}
                                                onClick={() => deleteDevice(device)}
                                            >
                                                Delete
                                            </button>
                                        </>
                                    )}
                                </div>
                            )}
                        </article>
                    ))}
                </div>
            )}
        </div>
    );
}

export default Devices;
