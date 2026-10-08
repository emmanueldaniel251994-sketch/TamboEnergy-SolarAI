import { API_BASE_URL } from "../config";
import { useCallback, useEffect, useState } from "react";

function Customers({ token }) {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showForm, setShowForm] = useState(false);

  // null = adding a new customer
  // customer ID = editing an existing customer
  const [editingId, setEditingId] = useState(null);

  const [formData, setFormData] = useState({
    name: "",
    phone: "",
    email: "",
    address: "",
  });

  // =========================================================
  // LOAD CUSTOMERS
  // =========================================================

  const loadCustomers = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_BASE_URL}/customers/`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to load customers."
        );
      }

      setCustomers(
        Array.isArray(data) ? data : []
      );
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadCustomers();
  }, [loadCustomers]);

  // =========================================================
  // HANDLE INPUT
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
      name: "",
      phone: "",
      email: "",
      address: "",
    });

    setEditingId(null);
  };

  // =========================================================
  // OPEN ADD FORM
  // =========================================================

  const handleAddCustomer = () => {
    resetForm();
    setError("");
    setSuccess("");

    setShowForm((current) => !current);
  };

  // =========================================================
  // OPEN EDIT FORM
  // =========================================================

  const handleEdit = (customer) => {
    setEditingId(customer.id);

    setFormData({
      name: customer.name || "",
      phone: customer.phone || "",
      email: customer.email || "",
      address: customer.address || "",
    });

    setError("");
    setSuccess("");
    setShowForm(true);

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  // =========================================================
  // CREATE OR UPDATE CUSTOMER
  // =========================================================

  const handleSubmit = async (event) => {
    event.preventDefault();

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const payload = {
        name: formData.name.trim(),
        phone: formData.phone.trim(),
        email: formData.email.trim(),
        address: formData.address.trim(),
      };

      if (!payload.name) {
        throw new Error(
          "Customer name is required."
        );
      }

      if (!payload.phone) {
        throw new Error(
          "Phone number is required."
        );
      }

      if (!payload.email) {
        throw new Error(
          "Email address is required."
        );
      }

      if (!payload.address) {
        throw new Error(
          "Address is required."
        );
      }

      const isEditing = editingId !== null;

      const url = isEditing
        ? `${API_BASE_URL}/customers/${editingId}`
        : `${API_BASE_URL}/customers/`;

      const response = await fetch(url, {
        method: isEditing ? "PUT" : "POST",

        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },

        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        let errorMessage = isEditing
          ? "Unable to update customer."
          : "Unable to create customer.";

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

      if (isEditing) {
        setSuccess(
          `${payload.name} updated successfully.`
        );
      } else {
        setSuccess(
          `${payload.name} added successfully.`
        );
      }

      resetForm();
      setShowForm(false);

      await loadCustomers();
    } catch (error) {
      setError(error.message);
    } finally {
      setSaving(false);
    }
  };

  // =========================================================
  // DELETE CUSTOMER
  // =========================================================

  const handleDelete = async (customer) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${customer.name}?\n\nThis action cannot be undone.`
    );

    if (!confirmed) {
      return;
    }

    setDeletingId(customer.id);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/customers/${customer.id}`,
        {
          method: "DELETE",

          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        let errorMessage =
          "Unable to delete customer.";

        try {
          const data = await response.json();

          if (
            typeof data.detail === "string"
          ) {
            errorMessage = data.detail;
          }
        } catch {
          // No JSON response
        }

        throw new Error(errorMessage);
      }

      setSuccess(
        `${customer.name} deleted successfully.`
      );

      // If the customer currently being edited
      // was deleted, close the form.
      if (editingId === customer.id) {
        resetForm();
        setShowForm(false);
      }

      await loadCustomers();
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
      {/* =====================================================
          PAGE HEADER
          ===================================================== */}

      <div className="page-header">
        <div>
          <p className="dashboard-label">
            CUSTOMER MANAGEMENT
          </p>

          <h1>Customers</h1>

          <p>
            Manage customers connected to
            TamboEnergy SolarAI.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={handleAddCustomer}
        >
          {showForm && editingId === null
            ? "Close Form"
            : "+ Add Customer"}
        </button>
      </div>

      {/* =====================================================
          ERROR
          ===================================================== */}

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {/* =====================================================
          SUCCESS
          ===================================================== */}

      {success && (
        <div className="success-message">
          {success}
        </div>
      )}

      {/* =====================================================
          ADD / EDIT CUSTOMER FORM
          ===================================================== */}

      {showForm && (
        <div className="solar-form-card">
          <div className="form-heading">
            <h2>
              {editingId !== null
                ? "Edit Customer"
                : "Add Customer"}
            </h2>

            <p>
              {editingId !== null
                ? "Update the customer's information."
                : "Enter the customer's contact information."}
            </p>
          </div>

          <form
            className="solar-form"
            onSubmit={handleSubmit}
          >
            <div className="form-grid">
              {/* CUSTOMER NAME */}

              <div className="form-group">
                <label htmlFor="name">
                  Customer Name
                </label>

                <input
                  id="name"
                  name="name"
                  type="text"
                  placeholder="Example: Daniel Emmanuel"
                  value={formData.name}
                  onChange={handleChange}
                  required
                />
              </div>

              {/* PHONE */}

              <div className="form-group">
                <label htmlFor="phone">
                  Phone Number
                </label>

                <input
                  id="phone"
                  name="phone"
                  type="tel"
                  placeholder="Example: 08012345678"
                  value={formData.phone}
                  onChange={handleChange}
                  required
                />
              </div>

              {/* EMAIL */}

              <div className="form-group">
                <label htmlFor="email">
                  Email Address
                </label>

                <input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="customer@example.com"
                  value={formData.email}
                  onChange={handleChange}
                  required
                />
              </div>

              {/* ADDRESS */}

              <div className="form-group">
                <label htmlFor="address">
                  Address
                </label>

                <input
                  id="address"
                  name="address"
                  type="text"
                  placeholder="Customer address"
                  value={formData.address}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div className="form-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => {
                  resetForm();
                  setShowForm(false);
                  setError("");
                }}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="primary-button"
                disabled={saving}
              >
                {saving
                  ? editingId !== null
                    ? "Updating..."
                    : "Adding..."
                  : editingId !== null
                    ? "Update Customer"
                    : "Add Customer"}
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
          <span>Total Customers</span>

          <strong>
            {customers.length}
          </strong>
        </div>
      </div>

      {/* =====================================================
          CUSTOMER TABLE
          ===================================================== */}

      <div className="systems-table-card">
        {loading ? (
          <div className="page-loading">
            Loading customers...
          </div>
        ) : customers.length === 0 ? (
          <div className="empty-state">
            No customers have been registered.
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Phone</th>
                  <th>Email</th>
                  <th>Address</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {customers.map((customer) => (
                  <tr key={customer.id}>
                    <td>
                      #{customer.id}
                    </td>

                    <td>
                      <strong>
                        {customer.name}
                      </strong>
                    </td>

                    <td>
                      {customer.phone || "—"}
                    </td>

                    <td>
                      {customer.email || "—"}
                    </td>

                    <td>
                      {customer.address || "—"}
                    </td>

                    <td>
                      <div className="table-actions">
                        <button
                          type="button"
                          className="edit-button"
                          onClick={() =>
                            handleEdit(customer)
                          }
                          disabled={
                            deletingId ===
                            customer.id
                          }
                        >
                          Edit
                        </button>

                        <button
                          type="button"
                          className="delete-button"
                          disabled={
                            deletingId ===
                            customer.id
                          }
                          onClick={() =>
                            handleDelete(customer)
                          }
                        >
                          {deletingId ===
                          customer.id
                            ? "Deleting..."
                            : "Delete"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default Customers;