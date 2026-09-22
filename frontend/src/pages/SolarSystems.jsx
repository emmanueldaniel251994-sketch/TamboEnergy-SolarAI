import { useCallback, useEffect, useState } from "react";

function SolarSystems({ token }) {
    // =========================================================
    // STATE
    // =========================================================

    const [systems, setSystems] = useState([]);
    const [customers, setCustomers] = useState([]);

    const [loading, setLoading] = useState(true);
    const [customersLoading, setCustomersLoading] =
        useState(true);

    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] =
        useState(null);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const [showForm, setShowForm] =
        useState(false);

    const [formData, setFormData] = useState({
        customer_id: "",
        inverter_brand: "",
        inverter_capacity_kva: "",
        battery_type: "",
        battery_capacity_kwh: "",
        panel_count: "",
        panel_wattage: "",
        location: "",
    });

    // =========================================================
    // LOAD SOLAR SYSTEMS
    // =========================================================

    const loadSolarSystems = useCallback(async () => {
        try {
            setLoading(true);

            const response = await fetch(
                "http://127.0.0.1:8000/solar-systems/",
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
                    "Unable to load solar systems."
                );
            }

            setSystems(
                Array.isArray(data) ? data : []
            );
        } catch (error) {
            setError(error.message);
        } finally {
            setLoading(false);
        }
    }, [token]);

    // =========================================================
    // LOAD CUSTOMERS
    // =========================================================

    const loadCustomers = useCallback(async () => {
        try {
            setCustomersLoading(true);

            const response = await fetch(
                "http://127.0.0.1:8000/customers/",
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
                    "Unable to load customers."
                );
            }

            setCustomers(
                Array.isArray(data) ? data : []
            );
        } catch (error) {
            setError(error.message);
        } finally {
            setCustomersLoading(false);
        }
    }, [token]);

    // =========================================================
    // LOAD PAGE DATA
    // =========================================================

    useEffect(() => {
        loadSolarSystems();
        loadCustomers();
    }, [loadSolarSystems, loadCustomers]);

    // =========================================================
    // HANDLE FORM INPUT
    // =========================================================

    const handleChange = (event) => {
        const { name, value } = event.target;

        setFormData((current) => ({
            ...current,
            [name]: value,
        }));
    };

    // =========================================================
    // RESET FORM
    // =========================================================

    const resetForm = () => {
        setFormData({
            customer_id: "",
            inverter_brand: "",
            inverter_capacity_kva: "",
            battery_type: "",
            battery_capacity_kwh: "",
            panel_count: "",
            panel_wattage: "",
            location: "",
        });
    };

    // =========================================================
    // GET CUSTOMER BY ID
    // =========================================================

    const getCustomer = (customerId) => {
        return customers.find(
            (customer) =>
                Number(customer.id) ===
                Number(customerId)
        );
    };

    // =========================================================
    // ADD SOLAR SYSTEM
    // =========================================================

    const handleSubmit = async (event) => {
        event.preventDefault();

        setSaving(true);
        setError("");
        setSuccess("");

        try {
            const payload = {
                customer_id: Number(
                    formData.customer_id
                ),

                inverter_brand:
                    formData.inverter_brand.trim(),

                inverter_capacity_kva: Number(
                    formData.inverter_capacity_kva
                ),

                battery_type:
                    formData.battery_type.trim(),

                battery_capacity_kwh: Number(
                    formData.battery_capacity_kwh
                ),

                panel_count: Number(
                    formData.panel_count
                ),

                panel_wattage: Number(
                    formData.panel_wattage
                ),

                location:
                    formData.location.trim(),
            };

            if (!payload.customer_id) {
                throw new Error(
                    "Please select a customer."
                );
            }

            if (!payload.inverter_brand) {
                throw new Error(
                    "Please enter the inverter brand."
                );
            }

            if (
                payload.inverter_capacity_kva <= 0
            ) {
                throw new Error(
                    "Inverter capacity must be greater than 0."
                );
            }

            if (!payload.battery_type) {
                throw new Error(
                    "Please select a battery type."
                );
            }

            if (
                payload.battery_capacity_kwh <= 0
            ) {
                throw new Error(
                    "Battery capacity must be greater than 0."
                );
            }

            if (payload.panel_count <= 0) {
                throw new Error(
                    "Panel count must be greater than 0."
                );
            }

            if (payload.panel_wattage <= 0) {
                throw new Error(
                    "Panel wattage must be greater than 0."
                );
            }

            if (!payload.location) {
                throw new Error(
                    "Please enter the installation location."
                );
            }

            const response = await fetch(
                "http://127.0.0.1:8000/solar-systems/",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        Authorization:
                            `Bearer ${token}`,
                    },

                    body: JSON.stringify(payload),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                let errorMessage =
                    "Unable to register solar system.";

                if (
                    typeof data.detail === "string"
                ) {
                    errorMessage = data.detail;
                } else if (
                    Array.isArray(data.detail)
                ) {
                    errorMessage = data.detail
                        .map((item) => item.msg)
                        .join(", ");
                }

                throw new Error(errorMessage);
            }

            setSuccess(
                "Solar system registered successfully."
            );

            resetForm();
            setShowForm(false);

            await loadSolarSystems();
        } catch (error) {
            setError(error.message);
        } finally {
            setSaving(false);
        }
    };

    // =========================================================
    // DELETE SOLAR SYSTEM
    // =========================================================

    const handleDelete = async (systemId) => {
        const confirmed = window.confirm(
            `Are you sure you want to delete Solar System #${systemId}?\n\nThis action cannot be undone.`
        );

        if (!confirmed) {
            return;
        }

        setDeletingId(systemId);
        setError("");
        setSuccess("");

        try {
            const response = await fetch(
                `http://127.0.0.1:8000/solar-systems/${systemId}`,
                {
                    method: "DELETE",

                    headers: {
                        Authorization:
                            `Bearer ${token}`,
                    },
                }
            );

            if (!response.ok) {
                let errorMessage =
                    "Unable to delete solar system.";

                try {
                    const data =
                        await response.json();

                    if (
                        typeof data.detail ===
                        "string"
                    ) {
                        errorMessage =
                            data.detail;
                    }
                } catch {
                    // No JSON body returned
                }

                throw new Error(errorMessage);
            }

            setSuccess(
                `Solar System #${systemId} deleted successfully.`
            );

            setSystems((currentSystems) =>
                currentSystems.filter(
                    (system) =>
                        system.id !== systemId
                )
            );

            await loadSolarSystems();
        } catch (error) {
            setError(error.message);
        } finally {
            setDeletingId(null);
        }
    };

    // =========================================================
    // PAGE
    // =========================================================

    return (
        <div className="page-content">
            {/* PAGE HEADER */}

            <div className="page-header">
                <div>
                    <p className="dashboard-label">
                        SYSTEM MANAGEMENT
                    </p>

                    <h1>Solar Systems</h1>

                    <p>
                        View and manage solar installations
                        connected to SolarAI.
                    </p>
                </div>

                <button
                    type="button"
                    className="primary-button"
                    onClick={() => {
                        setShowForm(
                            (current) => !current
                        );

                        setError("");
                        setSuccess("");
                    }}
                >
                    {showForm
                        ? "Close Form"
                        : "+ Add Solar System"}
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

            {/* =====================================================
          ADD SOLAR SYSTEM FORM
          ===================================================== */}

            {showForm && (
                <div className="solar-form-card">
                    <div className="form-heading">
                        <h2>
                            Register Solar System
                        </h2>

                        <p>
                            Select a customer and enter the
                            installation details.
                        </p>
                    </div>

                    <form
                        className="solar-form"
                        onSubmit={handleSubmit}
                    >
                        <div className="form-grid">
                            {/* CUSTOMER DROPDOWN */}

                            <div className="form-group">
                                <label htmlFor="customer_id">
                                    Customer
                                </label>

                                <select
                                    id="customer_id"
                                    name="customer_id"
                                    value={
                                        formData.customer_id
                                    }
                                    onChange={handleChange}
                                    disabled={
                                        customersLoading
                                    }
                                    required
                                >
                                    <option value="">
                                        {customersLoading
                                            ? "Loading customers..."
                                            : "Select customer"}
                                    </option>

                                    {customers.map(
                                        (customer) => (
                                            <option
                                                key={customer.id}
                                                value={customer.id}
                                            >
                                                {customer.name} —{" "}
                                                {customer.phone}
                                            </option>
                                        )
                                    )}
                                </select>

                                {!customersLoading &&
                                    customers.length === 0 && (
                                        <small className="form-help">
                                            No customers are available.
                                            Create a customer first.
                                        </small>
                                    )}
                            </div>

                            {/* INVERTER BRAND */}

                            <div className="form-group">
                                <label htmlFor="inverter_brand">
                                    Inverter Brand
                                </label>

                                <input
                                    id="inverter_brand"
                                    name="inverter_brand"
                                    type="text"
                                    placeholder="Example: Luxsun"
                                    value={
                                        formData.inverter_brand
                                    }
                                    onChange={handleChange}
                                    required
                                />
                            </div>

                            {/* INVERTER CAPACITY */}

                            <div className="form-group">
                                <label htmlFor="inverter_capacity_kva">
                                    Inverter Capacity (kVA)
                                </label>

                                <input
                                    id="inverter_capacity_kva"
                                    name="inverter_capacity_kva"
                                    type="number"
                                    min="0.1"
                                    step="0.1"
                                    placeholder="Example: 5"
                                    value={
                                        formData.inverter_capacity_kva
                                    }
                                    onChange={handleChange}
                                    required
                                />
                            </div>

                            {/* BATTERY TYPE */}

                            <div className="form-group">
                                <label htmlFor="battery_type">
                                    Battery Type
                                </label>

                                <select
                                    id="battery_type"
                                    name="battery_type"
                                    value={
                                        formData.battery_type
                                    }
                                    onChange={handleChange}
                                    required
                                >
                                    <option value="">
                                        Select battery type
                                    </option>

                                    <option value="Lithium">
                                        Lithium
                                    </option>

                                    <option value="Tubular">
                                        Tubular
                                    </option>

                                    <option value="AGM">
                                        AGM
                                    </option>

                                    <option value="Gel">
                                        Gel
                                    </option>

                                    <option value="Lead Acid">
                                        Lead Acid
                                    </option>
                                </select>
                            </div>

                            {/* BATTERY CAPACITY */}

                            <div className="form-group">
                                <label htmlFor="battery_capacity_kwh">
                                    Battery Capacity (kWh)
                                </label>

                                <input
                                    id="battery_capacity_kwh"
                                    name="battery_capacity_kwh"
                                    type="number"
                                    min="0.1"
                                    step="0.1"
                                    placeholder="Example: 5"
                                    value={
                                        formData.battery_capacity_kwh
                                    }
                                    onChange={handleChange}
                                    required
                                />
                            </div>

                            {/* PANEL COUNT */}

                            <div className="form-group">
                                <label htmlFor="panel_count">
                                    Number of Panels
                                </label>

                                <input
                                    id="panel_count"
                                    name="panel_count"
                                    type="number"
                                    min="1"
                                    step="1"
                                    placeholder="Example: 6"
                                    value={
                                        formData.panel_count
                                    }
                                    onChange={handleChange}
                                    required
                                />
                            </div>

                            {/* PANEL WATTAGE */}

                            <div className="form-group">
                                <label htmlFor="panel_wattage">
                                    Panel Wattage (W)
                                </label>

                                <input
                                    id="panel_wattage"
                                    name="panel_wattage"
                                    type="number"
                                    min="1"
                                    step="1"
                                    placeholder="Example: 550"
                                    value={
                                        formData.panel_wattage
                                    }
                                    onChange={handleChange}
                                    required
                                />
                            </div>

                            {/* LOCATION */}

                            <div className="form-group">
                                <label htmlFor="location">
                                    Installation Location
                                </label>

                                <input
                                    id="location"
                                    name="location"
                                    type="text"
                                    placeholder="Example: Ado-Ekiti"
                                    value={
                                        formData.location
                                    }
                                    onChange={handleChange}
                                    required
                                />
                            </div>
                        </div>

                        {/* SELECTED CUSTOMER INFO */}

                        {formData.customer_id && (
                            <div className="selected-customer">
                                {(() => {
                                    const customer =
                                        getCustomer(
                                            formData.customer_id
                                        );

                                    if (!customer) {
                                        return null;
                                    }

                                    return (
                                        <>
                                            <strong>
                                                Selected Customer
                                            </strong>

                                            <span>
                                                {customer.name}
                                            </span>

                                            <span>
                                                {customer.phone}
                                            </span>

                                            <span>
                                                {customer.email}
                                            </span>

                                            <span>
                                                {customer.address}
                                            </span>
                                        </>
                                    );
                                })()}
                            </div>
                        )}

                        {/* FORM ACTIONS */}

                        <div className="form-actions">
                            <button
                                type="button"
                                className="secondary-button"
                                onClick={() => {
                                    resetForm();
                                    setShowForm(false);
                                    setError("");
                                    setSuccess("");
                                }}
                            >
                                Cancel
                            </button>

                            <button
                                type="submit"
                                className="primary-button"
                                disabled={
                                    saving ||
                                    customers.length === 0
                                }
                            >
                                {saving
                                    ? "Registering..."
                                    : "Register Solar System"}
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* =====================================================
          SUMMARY
          ===================================================== */}

            <div className="page-summary">
                <div>
                    <span>Total Systems</span>

                    <strong>
                        {systems.length}
                    </strong>
                </div>
            </div>

            {/* =====================================================
          SOLAR SYSTEM TABLE
          ===================================================== */}

            <div className="systems-table-card">
                {loading ? (
                    <div className="page-loading">
                        Loading solar systems...
                    </div>
                ) : systems.length === 0 ? (
                    <div className="empty-state">
                        No solar systems have been
                        registered.
                    </div>
                ) : (
                    <div className="table-wrapper">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Customer</th>
                                    <th>Inverter</th>
                                    <th>Battery</th>
                                    <th>Panels</th>
                                    <th>PV Array</th>
                                    <th>Location</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>

                            <tbody>
                                {systems.map(
                                    (system) => {
                                        const customer =
                                            getCustomer(
                                                system.customer_id
                                            );

                                        const totalPanelPower =
                                            system.panel_count &&
                                                system.panel_wattage
                                                ? system.panel_count *
                                                system.panel_wattage
                                                : null;

                                        return (
                                            <tr key={system.id}>
                                                {/* ID */}

                                                <td>
                                                    #{system.id}
                                                </td>

                                                {/* CUSTOMER */}

                                                <td>
                                                    <strong>
                                                        {customer
                                                            ? customer.name
                                                            : `Customer #${system.customer_id}`}
                                                    </strong>

                                                    {customer && (
                                                        <div className="table-subtext">
                                                            {customer.phone}
                                                        </div>
                                                    )}
                                                </td>

                                                {/* INVERTER */}

                                                <td>
                                                    <strong>
                                                        {system.inverter_brand ||
                                                            "—"}
                                                    </strong>

                                                    <div className="table-subtext">
                                                        {system.inverter_capacity_kva !=
                                                            null
                                                            ? `${system.inverter_capacity_kva} kVA`
                                                            : "—"}
                                                    </div>
                                                </td>

                                                {/* BATTERY */}

                                                <td>
                                                    <strong>
                                                        {system.battery_type ||
                                                            "—"}
                                                    </strong>

                                                    <div className="table-subtext">
                                                        {system.battery_capacity_kwh !=
                                                            null
                                                            ? `${system.battery_capacity_kwh} kWh`
                                                            : "—"}
                                                    </div>
                                                </td>

                                                {/* PANELS */}

                                                <td>
                                                    {system.panel_count ??
                                                        "—"}{" "}
                                                    ×{" "}
                                                    {system.panel_wattage ??
                                                        "—"}{" "}
                                                    W
                                                </td>

                                                {/* PV ARRAY */}

                                                <td>
                                                    {totalPanelPower !==
                                                        null
                                                        ? `${totalPanelPower} W`
                                                        : "—"}
                                                </td>

                                                {/* LOCATION */}

                                                <td>
                                                    {system.location ||
                                                        "—"}
                                                </td>

                                                {/* DELETE */}

                                                <td>
                                                    <button
                                                        type="button"
                                                        className="delete-button"
                                                        disabled={
                                                            deletingId ===
                                                            system.id
                                                        }
                                                        onClick={() =>
                                                            handleDelete(
                                                                system.id
                                                            )
                                                        }
                                                    >
                                                        {deletingId ===
                                                            system.id
                                                            ? "Deleting..."
                                                            : "Delete"}
                                                    </button>
                                                </td>
                                            </tr>
                                        );
                                    }
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}

export default SolarSystems;