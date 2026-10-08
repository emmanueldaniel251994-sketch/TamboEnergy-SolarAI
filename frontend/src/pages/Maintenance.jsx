import { API_BASE_URL } from "../config";
import { useEffect, useState } from "react";

const emptyForm = {
  solar_system_id: "",
  issue: "",
  action_taken: "",
  status: "open",
  technician: "",
};

function Maintenance({ token }) {
  const [records, setRecords] = useState([]);
  const [solarSystems, setSolarSystems] = useState([]);

  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionId, setActionId] = useState(null);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // ============================================================
  // LOAD MAINTENANCE RECORDS
  // ============================================================

  const loadMaintenance = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/maintenance/`,
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
            "Unable to load maintenance records."
        );
      }

      const maintenanceRecords =
        Array.isArray(data) ? data : [];

      maintenanceRecords.sort(
        (a, b) => Number(b.id) - Number(a.id)
      );

      setRecords(maintenanceRecords);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // LOAD SOLAR SYSTEMS
  // ============================================================

  const loadSolarSystems = async () => {
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
          data.detail ||
            "Unable to load solar systems."
        );
      }

      setSolarSystems(
        Array.isArray(data) ? data : []
      );
    } catch (err) {
      setError(err.message);
    }
  };

  // ============================================================
  // INITIAL LOAD
  // ============================================================

  useEffect(() => {
    loadMaintenance();
    loadSolarSystems();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ============================================================
  // FORM CHANGE
  // ============================================================

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  };

  // ============================================================
  // RESET FORM
  // ============================================================

  const resetForm = () => {
    setForm(emptyForm);
    setEditingId(null);
  };

  // ============================================================
  // CREATE / UPDATE
  // ============================================================

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!form.solar_system_id && !editingId) {
      setError("Please select a solar system.");
      return;
    }

    if (!form.issue.trim()) {
      setError("Please enter the maintenance issue.");
      return;
    }

    setSaving(true);

    try {
      const url = editingId
        ? `${API_BASE_URL}/maintenance/${editingId}`
        : `${API_BASE_URL}/maintenance/`;

      let body;

      if (editingId) {
        body = {
          issue: form.issue.trim(),
          action_taken:
            form.action_taken.trim() || null,
          status: form.status,
          technician:
            form.technician.trim() || null,
        };
      } else {
        body = {
          solar_system_id: Number(
            form.solar_system_id
          ),
          issue: form.issue.trim(),
          action_taken:
            form.action_taken.trim() || null,
          status: form.status,
          technician:
            form.technician.trim() || null,
        };
      }

      const response = await fetch(url, {
        method: editingId ? "PUT" : "POST",

        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },

        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Unable to save maintenance record."
        );
      }

      setSuccess(
        editingId
          ? `Maintenance record #${editingId} updated successfully.`
          : `Maintenance record #${data.id} created successfully.`
      );

      resetForm();
      await loadMaintenance();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  // ============================================================
  // EDIT
  // ============================================================

  const handleEdit = (record) => {
    setEditingId(record.id);

    setForm({
      solar_system_id: String(
        record.solar_system_id
      ),
      issue: record.issue || "",
      action_taken:
        record.action_taken || "",
      status: record.status || "open",
      technician:
        record.technician || "",
    });

    setError("");
    setSuccess("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  // ============================================================
  // DELETE
  // ============================================================

  const handleDelete = async (record) => {
    const confirmed = window.confirm(
      `Permanently delete maintenance record #${record.id}?\n\n` +
        `Issue: ${record.issue}\n\n` +
        "This action cannot be undone."
    );

    if (!confirmed) {
      return;
    }

    setActionId(record.id);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/maintenance/${record.id}`,
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
            "Unable to delete maintenance record."
        );
      }

      setRecords((currentRecords) =>
        currentRecords.filter(
          (item) => item.id !== record.id
        )
      );

      if (editingId === record.id) {
        resetForm();
      }

      setSuccess(
        `Maintenance record #${record.id} deleted successfully.`
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setActionId(null);
    }
  };

  // ============================================================
  // DATE FORMAT
  // ============================================================

  const formatDate = (date) => {
    if (!date) {
      return "—";
    }

    const parsed = new Date(date);

    if (Number.isNaN(parsed.getTime())) {
      return date;
    }

    return parsed.toLocaleString();
  };

  // ============================================================
  // STATUS CLASS
  // ============================================================

  const getStatusClass = (status) => {
    const normalized =
      String(status || "")
        .toLowerCase()
        .replace(/\s+/g, "-");

    return `maintenance-status status-${normalized}`;
  };

  // ============================================================
  // PAGE
  // ============================================================

  return (
    <div className="maintenance-page">

      {/* PAGE HEADER */}

      <div className="page-header">
        <div>
          <h1>Maintenance</h1>

          <p>
            Manage solar system maintenance,
            repairs and technician service history.
          </p>
        </div>

        <button
          type="button"
          className="secondary-button"
          onClick={loadMaintenance}
          disabled={loading}
        >
          {loading
            ? "Refreshing..."
            : "Refresh Records"}
        </button>
      </div>

      {/* ERROR */}

      {error && (
        <div className="diagnostic-message">
          {error}
        </div>
      )}

      {/* SUCCESS */}

      {success && (
        <div className="success-message">
          {success}
        </div>
      )}

      {/* FORM */}

      <div className="maintenance-form-card">

        <div className="maintenance-form-heading">
          <div>
            <h2>
              {editingId
                ? `Edit Maintenance #${editingId}`
                : "Add Maintenance Record"}
            </h2>

            <p>
              Record faults, repairs and
              maintenance work carried out on a
              solar installation.
            </p>
          </div>

          {editingId && (
            <button
              type="button"
              className="secondary-button"
              onClick={resetForm}
            >
              Cancel Edit
            </button>
          )}
        </div>

        <form
          className="maintenance-form"
          onSubmit={handleSubmit}
        >

          <div className="maintenance-form-grid">

            {/* SOLAR SYSTEM */}

            <div className="form-group">
              <label htmlFor="solar_system_id">
                Solar System
              </label>

              <select
                id="solar_system_id"
                name="solar_system_id"
                value={form.solar_system_id}
                onChange={handleChange}
                disabled={
                  Boolean(editingId) ||
                  saving
                }
                required={!editingId}
              >
                <option value="">
                  Select solar system
                </option>

                {solarSystems.map(
                  (system) => (
                    <option
                      key={system.id}
                      value={system.id}
                    >
                      System #{system.id}
                      {system.location
                        ? ` — ${system.location}`
                        : ""}
                    </option>
                  )
                )}
              </select>
            </div>

            {/* STATUS */}

            <div className="form-group">
              <label htmlFor="status">
                Status
              </label>

              <select
                id="status"
                name="status"
                value={form.status}
                onChange={handleChange}
                disabled={saving}
              >
                <option value="open">
                  Open
                </option>

                <option value="in_progress">
                  In Progress
                </option>

                <option value="completed">
                  Completed
                </option>

                <option value="cancelled">
                  Cancelled
                </option>
              </select>
            </div>

            {/* TECHNICIAN */}

            <div className="form-group">
              <label htmlFor="technician">
                Technician
              </label>

              <input
                id="technician"
                name="technician"
                type="text"
                value={form.technician}
                onChange={handleChange}
                placeholder="Technician name"
                disabled={saving}
              />
            </div>

          </div>

          {/* ISSUE */}

          <div className="form-group">
            <label htmlFor="issue">
              Issue
            </label>

            <textarea
              id="issue"
              name="issue"
              value={form.issue}
              onChange={handleChange}
              placeholder="Describe the fault or maintenance issue..."
              rows="4"
              disabled={saving}
              required
            />
          </div>

          {/* ACTION TAKEN */}

          <div className="form-group">
            <label htmlFor="action_taken">
              Action Taken
            </label>

            <textarea
              id="action_taken"
              name="action_taken"
              value={form.action_taken}
              onChange={handleChange}
              placeholder="Describe inspection, repair or maintenance performed..."
              rows="4"
              disabled={saving}
            />
          </div>

          <div className="maintenance-form-actions">

            <button
              type="submit"
              className="primary-button"
              disabled={saving}
            >
              {saving
                ? "Saving..."
                : editingId
                ? "Update Record"
                : "Add Maintenance"}
            </button>

            {editingId && (
              <button
                type="button"
                className="secondary-button"
                onClick={resetForm}
                disabled={saving}
              >
                Cancel
              </button>
            )}

          </div>

        </form>
      </div>

      {/* RECORD SUMMARY */}

      <div className="maintenance-summary">

        <div className="analysis-card">
          <span>Total Records</span>
          <strong>{records.length}</strong>
        </div>

        <div className="analysis-card">
          <span>Open</span>

          <strong>
            {
              records.filter(
                (record) =>
                  record.status === "open"
              ).length
            }
          </strong>
        </div>

        <div className="analysis-card">
          <span>In Progress</span>

          <strong>
            {
              records.filter(
                (record) =>
                  record.status ===
                  "in_progress"
              ).length
            }
          </strong>
        </div>

        <div className="analysis-card">
          <span>Completed</span>

          <strong>
            {
              records.filter(
                (record) =>
                  record.status ===
                  "completed"
              ).length
            }
          </strong>
        </div>

      </div>

      {/* MAINTENANCE HISTORY */}

      <div className="maintenance-history">

        <div className="maintenance-history-heading">
          <div>
            <h2>
              Maintenance History
            </h2>

            <p>
              Service and repair records for
              registered solar systems.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="diagnostic-empty-state">
            <h3>
              Loading maintenance records...
            </h3>
          </div>
        ) : records.length === 0 ? (
          <div className="diagnostic-empty-state">
            <h3>
              No maintenance records
            </h3>

            <p>
              Maintenance records will appear
              here after they are created.
            </p>
          </div>
        ) : (
          <div className="maintenance-list">

            {records.map((record) => (

              <div
                className="maintenance-card"
                key={record.id}
              >

                <div className="maintenance-card-header">

                  <div>
                    <span className="diagnostic-label">
                      MAINTENANCE #
                      {record.id}
                    </span>

                    <h3>
                      {record.issue}
                    </h3>
                  </div>

                  <span
                    className={getStatusClass(
                      record.status
                    )}
                  >
                    {record.status
                      ?.replaceAll("_", " ")}
                  </span>

                </div>

                <div className="maintenance-details">

                  <div>
                    <span>
                      Solar System
                    </span>

                    <strong>
                      #{record.solar_system_id}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Technician
                    </span>

                    <strong>
                      {record.technician ||
                        "Not assigned"}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Created
                    </span>

                    <strong>
                      {formatDate(
                        record.created_at
                      )}
                    </strong>
                  </div>

                </div>

                <div className="maintenance-action-taken">
                  <strong>
                    Action Taken
                  </strong>

                  <p>
                    {record.action_taken ||
                      "No action recorded yet."}
                  </p>
                </div>

                <div className="maintenance-card-actions">

                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() =>
                      handleEdit(record)
                    }
                    disabled={
                      actionId === record.id
                    }
                  >
                    Edit
                  </button>

                  <button
                    type="button"
                    className="delete-button"
                    onClick={() =>
                      handleDelete(record)
                    }
                    disabled={
                      actionId === record.id
                    }
                  >
                    {actionId === record.id
                      ? "Deleting..."
                      : "Delete"}
                  </button>

                </div>

              </div>
            ))}

          </div>
        )}

      </div>

    </div>
  );
}

export default Maintenance;