import { useEffect, useState } from "react";
import "./App.css";
import { API_BASE_URL } from "./config";
import SolarSystems from "./pages/SolarSystems";
import Customers from "./pages/Customers";
import Alerts from "./pages/Alerts";
import Diagnostics from "./pages/Diagnostics";
import Maintenance from "./pages/Maintenance";
import Analytics from "./pages/Analytics";
import Telemetry from "./pages/Telemetry";
import Devices from "./pages/Devices";
import AIAssistant from "./pages/AIAssistant";

function App() {
  // =========================================================
  // STATE
  // =========================================================

  const [token, setToken] = useState(
    localStorage.getItem("solarai_token")
  );

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const [dashboard, setDashboard] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [dashboardLoading, setDashboardLoading] =
    useState(false);

  const [activePage, setActivePage] =
    useState("dashboard");

  // =========================================================
  // LOGIN
  // =========================================================

  const handleLogin = async (event) => {
    event.preventDefault();

    setLoading(true);
    setMessage("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/auth/login`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Login failed"
        );
      }

      if (!data.access_token) {
        throw new Error(
          "Login succeeded but no access token was returned."
        );
      }

      localStorage.setItem(
        "solarai_token",
        data.access_token
      );

      setToken(data.access_token);
      setActivePage("dashboard");
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // LOGOUT
  // =========================================================

  const handleLogout = () => {
    localStorage.removeItem("solarai_token");

    setToken(null);
    setDashboard(null);
    setCurrentUser(null);
    setEmail("");
    setPassword("");
    setMessage("");
    setActivePage("dashboard");
  };

  // =========================================================
  // LOAD DASHBOARD
  // =========================================================

  useEffect(() => {
    if (!token) {
      return;
    }

    const loadDashboard = async () => {
      setDashboardLoading(true);
      setMessage("");

      try {
        const response = await fetch(
          `${API_BASE_URL}/dashboard/summary`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.status === 401) {
          localStorage.removeItem(
            "solarai_token"
          );

          setToken(null);

          throw new Error(
            "Your session has expired. Please sign in again."
          );
        }

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.detail ||
            "Unable to load dashboard"
          );
        }

        setDashboard(data);
      } catch (error) {
        setMessage(error.message);
      } finally {
        setDashboardLoading(false);
      }
    };

    loadDashboard();
  }, [token]);

  // =========================================================
  // LOAD CURRENT USER PROFILE
  // =========================================================

  useEffect(() => {
    if (!token) {
      setCurrentUser(null);
      return;
    }

    const loadCurrentUser = async () => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/auth/me`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.detail || "Unable to load user profile"
          );
        }

        setCurrentUser(data);
      } catch (error) {
        if (error.message.toLowerCase().includes("token")) {
          localStorage.removeItem("solarai_token");
          setToken(null);
        }
        setMessage(error.message);
      }
    };

    loadCurrentUser();
  }, [token]);

  // =========================================================
  // LOGIN PAGE
  // =========================================================

  if (!token) {
    return (
      <div className="login-page">
        {/* LEFT BRAND PANEL */}

        <div className="brand-panel">
          <div className="brand-content">
            <div className="brand-badge">
              TAMBOENERGY
            </div>

            <h1>
              Solar<span>AI</span>
            </h1>

            <h2>
              Intelligent Solar Energy Management
            </h2>

            <p>
              Monitor solar systems, detect faults,
              analyze performance and manage
              maintenance from one intelligent
              platform.
            </p>

            <div className="feature-list">
              <div>
                ✓ Real-time solar monitoring
              </div>

              <div>
                ✓ AI-assisted diagnostics
              </div>

              <div>
                ✓ Intelligent fault alerts
              </div>

              <div>
                ✓ System health analytics
              </div>
            </div>
          </div>
        </div>

        {/* LOGIN PANEL */}

        <div className="login-panel">
          <form
            className="login-card"
            onSubmit={handleLogin}
          >
            <div className="mobile-brand">
              TAMBOENERGY SOLARAI
            </div>

            <p className="welcome">
              Welcome back
            </p>

            <h2>
              Sign in to SolarAI
            </h2>

            <p className="subtitle">
              Access your solar monitoring and
              diagnostic dashboard.
            </p>

            <label htmlFor="email">
              Email address
            </label>

            <input
              id="email"
              type="email"
              placeholder="admin@example.com"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              required
            />

            <label htmlFor="password">
              Password
            </label>

            <input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              required
            />

            <button
              type="submit"
              disabled={loading}
            >
              {loading
                ? "Signing in..."
                : "Sign In"}
            </button>

            {message && (
              <div className="login-message">
                {message}
              </div>
            )}

            <p className="footer-text">
              TamboEnergy System • SolarAI Platform
            </p>
          </form>
        </div>
      </div>
    );
  }

  // =========================================================
  // DASHBOARD LOADING
  // =========================================================

  if (dashboardLoading) {
    return (
      <div className="dashboard-loading">
        Loading SolarAI dashboard...
      </div>
    );
  }

  // =========================================================
  // MAIN APPLICATION
  // =========================================================

  return (
    <div className="dashboard-layout">
      {/* =====================================================
          SIDEBAR
          ===================================================== */}

      <aside className="sidebar">
        <div className="sidebar-logo">
          <span>TAMBOENERGY</span>

          <h2>
            Solar<span>AI</span>
          </h2>
        </div>

        <nav className="sidebar-menu">
          {/* DASHBOARD */}

          <button
            className={
              activePage === "dashboard"
                ? "active"
                : ""
            }
            onClick={() =>
              setActivePage("dashboard")
            }
          >
            Dashboard
          </button>

          {/* SOLAR SYSTEMS */}

          <button
            className={
              activePage === "systems"
                ? "active"
                : ""
            }
            onClick={() =>
              setActivePage("systems")
            }
          >
            Solar Systems
          </button>

          {/* CUSTOMERS */}

          <button
            className={
              activePage === "customers"
                ? "active"
                : ""
            }
            onClick={() =>
              setActivePage("customers")
            }
          >
            Customers
          </button>
          {/* LIVE MONITORING */}

          <button
            className={
              activePage === "telemetry"
                ? "active"
                : ""
            }
            onClick={() =>
              setActivePage("telemetry")
            }
          >
            Live Monitoring
          </button>

          {/* DEVICES */}

          <button
            className={
              activePage === "devices"
                ? "active"
                : ""
            }
            onClick={() =>
              setActivePage("devices")
            }
          >
            Devices
          </button>

          {/* OPERATIONS */}

          <button
            className={
              activePage === "alerts"
                ? "active"
                : ""
            }
            onClick={() =>
              setActivePage("alerts")
            }
          >
            Alerts
          </button>
          <button
            className={
              activePage === "diagnostics"
                ? "active"
                : ""
            }
            onClick={() =>
              setActivePage("diagnostics")
            }
          >
            Diagnostics
          </button>

          <button
            className={
              activePage === "maintenance"
                ? "active"
                : ""
            }
            onClick={() =>
              setActivePage("maintenance")
            }
          >
            Maintenance
          </button>
          <button
            className={
              activePage === "analytics"
                ? "active"
                : ""
            }
            onClick={() =>
              setActivePage("analytics")
            }
          >
            Analytics
          </button>

          <button className={activePage === "ai-assistant" ? "active" : ""} onClick={() => setActivePage("ai-assistant")}>AI Assistant</button>
        </nav>

        <div className="sidebar-bottom">
          {currentUser && (
            <div className="sidebar-user">
              <strong>{currentUser.full_name}</strong>
              <span>{currentUser.role}</span>
            </div>
          )}

          <button
            className="logout-button"
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>
      </aside>

      {/* =====================================================
          MAIN CONTENT
          ===================================================== */}
      <main className="dashboard-main">
        {activePage === "ai-assistant" ? (
          <AIAssistant token={token} />
        ) : activePage === "systems" ? (
          <SolarSystems token={token} />
        ) : activePage === "telemetry" ? (
          <Telemetry token={token} />
        ) : activePage === "customers" ? (
          <Customers token={token} />
        ) : activePage === "devices" ? (
          <Devices token={token} currentUser={currentUser} />
        ) : activePage === "alerts" ? (
          <Alerts token={token} currentUser={currentUser} />
        ) : activePage === "diagnostics" ? (
          <Diagnostics token={token} />
        ) : activePage === "maintenance" ? (
          <Maintenance token={token} />
        ) : activePage === "analytics" ? (
          <Analytics token={token} />
        ) : (

          <>
            {/* ===============================================
                DASHBOARD HEADER
                =============================================== */}

            <header className="dashboard-header">
              <div>
                <p className="dashboard-label">
                  SOLARAI CONTROL CENTER
                </p>

                <h1>
                  Solar System Dashboard
                </h1>

                <p>
                  Monitor system health, alerts
                  and AI-assisted diagnostics.
                </p>
              </div>

              <div className="live-indicator">
                <span></span>
                API Connected
              </div>
            </header>

            {/* DASHBOARD ERROR / MESSAGE */}

            {message && (
              <div className="dashboard-message">
                {message}
              </div>
            )}

            {/* ===============================================
                SUMMARY CARDS
                =============================================== */}

            <section className="summary-grid">
              <div className="summary-card">
                <p>
                  Solar Systems
                </p>

                <h2>
                  {dashboard?.total_solar_systems ??
                    0}
                </h2>

                <span>
                  Registered systems
                </span>
              </div>

              <div className="summary-card">
                <p>
                  Active Alerts
                </p>

                <h2>
                  {dashboard?.active_alerts ?? 0}
                </h2>

                <span>
                  Require attention
                </span>
              </div>

              <div className="summary-card">
                <p>
                  Critical Alerts
                </p>

                <h2>
                  {dashboard?.critical_alerts ??
                    0}
                </h2>

                <span>
                  Critical conditions
                </span>
              </div>

              <div className="summary-card">
                <p>
                  Needs Review
                </p>

                <h2>
                  {dashboard?.needs_review ?? 0}
                </h2>

                <span>
                  Technician review
                </span>
              </div>
            </section>

            {/* ===============================================
                SYSTEM HEALTH
                =============================================== */}

            <section className="dashboard-section">
              <div className="section-heading">
                <div>
                  <h2>
                    System Health
                  </h2>

                  <p>
                    Latest telemetry from your
                    registered solar systems.
                  </p>
                </div>
              </div>

              <div className="system-grid">
                {dashboard?.system_health?.length ? (
                  dashboard.system_health.map(
                    (system) => (
                      <div
                        className="system-card"
                        key={
                          system.solar_system_id
                        }
                      >
                        {/* CARD HEADER */}

                        <div className="system-card-header">
                          <div>
                            <span>
                              SOLAR SYSTEM
                            </span>

                            <h3>
                              System #
                              {
                                system.solar_system_id
                              }
                            </h3>
                          </div>

                          <div
                            className={`health-badge ${system.health_status ||
                              "unknown"
                              }`}
                          >
                            {system.health_status ||
                              "Unknown"}
                          </div>
                        </div>

                        {/* HEALTH SCORE */}

                        <div className="health-score">
                          <strong>
                            {system.health_score ??
                              "--"}
                          </strong>

                          <span>
                            /100 Health Score
                          </span>
                        </div>

                        {/* SYSTEM METRICS */}

                        <div className="metrics-grid">
                          <div>
                            <span>
                              Battery
                            </span>

                            <strong>
                              {system.battery_soc ??
                                "--"}
                              %
                            </strong>
                          </div>

                          <div>
                            <span>
                              PV Power
                            </span>

                            <strong>
                              {system.pv_power ??
                                "--"}{" "}
                              W
                            </strong>
                          </div>

                          <div>
                            <span>
                              Load
                            </span>

                            <strong>
                              {system.load_power ??
                                "--"}{" "}
                              W
                            </strong>
                          </div>

                          <div>
                            <span>
                              Temperature
                            </span>

                            <strong>
                              {system.temperature ??
                                "--"}
                              °C
                            </strong>
                          </div>
                        </div>

                        {/* DIAGNOSIS */}

                        <div className="diagnosis-box">
                          <span>
                            Latest Diagnosis
                          </span>

                          <strong>
                            {system.final_diagnosis ||
                              system.fault_type ||
                              "No diagnosis"}
                          </strong>
                        </div>
                      </div>
                    )
                  )
                ) : (
                  <div className="empty-state">
                    No solar systems available.
                  </div>
                )}
              </div>
            </section>

            {/* ===============================================
                RECENT ALERTS
                =============================================== */}

            <section className="dashboard-section">
              <div className="section-heading">
                <div>
                  <h2>
                    Recent Alerts
                  </h2>

                  <p>
                    Latest system warnings and
                    critical conditions.
                  </p>
                </div>
              </div>

              <div className="alert-list">
                {dashboard?.recent_alerts?.length ? (
                  dashboard.recent_alerts.map(
                    (alert) => (
                      <div
                        className="alert-row"
                        key={alert.id}
                      >
                        <div>
                          <span
                            className={`alert-severity ${alert.severity}`}
                          >
                            {alert.severity}
                          </span>

                          <strong>
                            {alert.title}
                          </strong>

                          <p>
                            {alert.message}
                          </p>
                        </div>

                        <span className="alert-status">
                          {alert.status}
                        </span>
                      </div>
                    )
                  )
                ) : (
                  <div className="empty-state">
                    No recent alerts.
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default App;