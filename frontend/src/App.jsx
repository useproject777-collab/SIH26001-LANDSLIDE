import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import MapView from "./MapView";
import { API_BASE, apiGet, apiPost } from "./api";
import "./App.css";

const DEFAULT_LOCATION_ID = 1;
const REFRESH_MS = 5 * 60 * 1000;

const RISK_COLORS = {
  LOW: "#22c55e",
  MEDIUM: "#f59e0b",
  HIGH: "#ef4444",
  CRITICAL: "#991b1b",
};

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "short",
  });
}

function riskClass(level = "LOW") {
  return `risk-pill risk-${level.toLowerCase()}`;
}

function App() {
  const [risk, setRisk] = useState(null);
  const [locations, setLocations] = useState([]);
  const [history, setHistory] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [selectedCoordinate, setSelectedCoordinate] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [focusCoordinate, setFocusCoordinate] = useState(null);
  const [satelliteEnabled, setSatelliteEnabled] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [stateSummary, setStateSummary] = useState([]);
  const [modelStatus, setModelStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [terrainBusy, setTerrainBusy] = useState(false);
  const [error, setError] = useState("");
  const [lastRefresh, setLastRefresh] = useState(null);
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [activeSource, setActiveSource] = useState("default");

  const currentIsRaining =
    Number(risk?.current_rain_mm || 0) > 0 ||
    Number(risk?.rainfall_1h || 0) > 0;

  const refreshDefault = useCallback(async () => {
    const [live, hist] = await Promise.all([
      apiGet(`/api/live-risk/${DEFAULT_LOCATION_ID}`),
      apiGet(`/api/risk-history/${DEFAULT_LOCATION_ID}`),
    ]);
    setRisk(live);
    setHistory(hist.slice().reverse());
  }, []);

  const refreshGlobal = useCallback(async () => {
    const [all, summary, activeAlerts, status, states] = await Promise.all([
      apiGet("/api/live-risk-all"),
      apiGet("/api/analytics/summary"),
      apiGet("/api/alerts?status=ACTIVE"),
      apiGet("/api/ml/status"),
      apiGet("/api/analytics/state-summary"),
    ]);
    setLocations(all);
    setAnalytics(summary);
    setAlerts(activeAlerts);
    setModelStatus(status);
    setStateSummary(states);
  }, []);

  const refreshEverything = useCallback(async () => {
    try {
      setError("");
      if (activeSource === "default") {
        await Promise.all([refreshDefault(), refreshGlobal()]);
      } else {
        await refreshGlobal();
      }
      setLastRefresh(new Date());
    } catch (err) {
      console.error(err);
      setError("Backend or live data service unavailable.");
    } finally {
      setLoading(false);
    }
  }, [activeSource, refreshDefault, refreshGlobal]);

  useEffect(() => {
    refreshEverything();
    const interval = setInterval(refreshEverything, REFRESH_MS);
    return () => clearInterval(interval);
  }, [refreshEverything]);

  useEffect(() => {
    if (!notificationsEnabled || !alerts.length) return;
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    const latest = alerts[0];
    new Notification(`${latest.risk_level} landslide risk`, {
      body: latest.message,
    });
  }, [alerts, notificationsEnabled]);

  const counts = useMemo(() => {
    const out = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
    locations.forEach((item) => {
      if (out[item.risk_level] !== undefined) out[item.risk_level] += 1;
    });
    return out;
  }, [locations]);

  const pieData = [
    { name: "LOW", value: counts.LOW },
    { name: "MEDIUM", value: counts.MEDIUM },
    { name: "HIGH", value: counts.HIGH },
    { name: "CRITICAL", value: counts.CRITICAL },
  ].filter((item) => item.value > 0);

  const runRiskForCoordinates = useCallback(
    async (latitude, longitude, label = "Selected Location") => {
      setBusy(true);
      try {
        const result = await apiGet(
          `/api/risk-by-coordinates?latitude=${latitude}&longitude=${longitude}`
        );
        const merged = {
          ...result,
          searched_place: label,
          location: label,
          latitude,
          longitude,
        };
        setRisk(merged);
        setActiveSource("custom");
        setHistory([]);
        setSelectedCoordinate({ latitude, longitude });
        setSelectedLocation(null);
        setFocusCoordinate({ latitude, longitude });
        setError("");
      } catch (err) {
        console.error(err);
        setError("Unable to calculate risk for this coordinate.");
      } finally {
        setBusy(false);
      }
    },
    []
  );

  const performSearch = async () => {
    const query = searchQuery.trim();
    if (!query) return;

    setBusy(true);
    setSearchResults([]);
    try {
      // First use known NER monitoring points.
      const local = locations.filter((item) =>
        [item.location_name, item.district, item.state]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query.toLowerCase()))
      );

      if (local.length > 0) {
        setSearchResults(
          local.slice(0, 8).map((item) => ({
            ...item,
            search_source: "NER monitoring database",
          }))
        );
        setBusy(false);
        return;
      }

      // Fallback to Open-Meteo geocoding via its public API.
      const response = await fetch(
        `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query)}&count=8&language=en&format=json`
      );
      if (!response.ok) throw new Error("Geocoding failed");
      const data = await response.json();
      const results = (data.results || []).map((place) => ({
        id: `geo-${place.id}`,
        location_name: place.name,
        district: place.admin2 || place.admin1 || "",
        state: place.admin1 || "",
        country: place.country || "",
        latitude: place.latitude,
        longitude: place.longitude,
        search_source: "Open-Meteo geocoding",
      }));
      setSearchResults(results);
      if (!results.length) setError(`No location found for “${query}”.`);
    } catch (err) {
      console.error(err);
      setError("Location search failed.");
    } finally {
      setBusy(false);
    }
  };

  const handleSearchResult = (item) => {
    const label = item.location_name || "Selected Location";
    runRiskForCoordinates(item.latitude, item.longitude, label);
    setSearchResults([]);
    setSearchQuery(label);
  };

 const useCurrentLocation = () => {
  if (!navigator.geolocation) {
    setError("Geolocation is not supported by this browser.");
    return;
  }

  setBusy(true);
  setError("");

  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      const { latitude, longitude, accuracy } = coords;

      console.log("Browser location:", {
        latitude,
        longitude,
        accuracy_m: accuracy,
      });

      // Desktop/browser location can sometimes be very inaccurate.
      if (accuracy > 50000) {
  setBusy(false);
  setError(
    `⚠️ Your browser could not determine your precise location (accuracy ±${(
      accuracy / 1000
    ).toFixed(1)} km). Please enable Windows Location Services or search your city.`
  );
  return;
}

      runRiskForCoordinates(
        latitude,
        longitude,
        `My Current Location (±${Math.round(accuracy)} m)`
      ).finally(() => setBusy(false));
    },

    (geoError) => {
      setBusy(false);

      if (geoError.code === 1) {
        setError(
          "Location permission was denied. Please allow location access."
        );
      } else if (geoError.code === 2) {
        setError(
          "Current location is unavailable. Please enable Windows Location Services."
        );
      } else if (geoError.code === 3) {
        setError(
          "Location request timed out. Please try again."
        );
      } else {
        setError("Unable to get the current location.");
      }
    },

    {
      enableHighAccuracy: true,
      timeout: 30000,
      maximumAge: 0,
    }
  );
};

  const acknowledgeAlert = async (id) => {
    try {
      await apiPost(`/api/alerts/${id}/acknowledge`);
      const updated = await apiGet("/api/alerts?status=ACTIVE");
      setAlerts(updated);
    } catch (err) {
      console.error(err);
      setError("Could not acknowledge alert.");
    }
  };

  const enableNotifications = async () => {
    if (!("Notification" in window)) {
      setError("Browser notifications are not supported.");
      return;
    }
    const permission = await Notification.requestPermission();
    setNotificationsEnabled(permission === "granted");
  };

  const refreshTerrain = async () => {
    setTerrainBusy(true);
    try {
      await apiPost("/api/terrain/refresh-all");
      await refreshGlobal();
      setError("");
    } catch (err) {
      console.error(err);
      setError("Terrain refresh failed. Check the backend/elevation service.");
    } finally {
      setTerrainBusy(false);
    }
  };

  const selectMarker = (location) => {
    setActiveSource("default");
    setSelectedLocation(location);
    setRisk((current) => ({ ...current, ...location, searched_place: location.location_name }));
    setSelectedCoordinate({
      latitude: location.latitude,
      longitude: location.longitude,
    });
    setFocusCoordinate({
      latitude: location.latitude,
      longitude: location.longitude,
    });
  };

  const handleMapClick = ({ latitude, longitude }) => {
    runRiskForCoordinates(latitude, longitude, "Map Selected Location");
  };

  const exportLocations = () => {
    const headers = [
      "Location", "State", "District", "Latitude", "Longitude",
      "Temperature", "Rainfall_24h", "Slope_degree", "Risk_score", "Risk_level"
    ];
    const rows = locations.map((item) => [
      item.location_name, item.state, item.district, item.latitude, item.longitude,
      item.temperature ?? "", item.rainfall_24h ?? "", item.slope_degree ?? "",
      item.risk_score ?? "", item.risk_level ?? ""
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ner_landslide_live_monitoring.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`app-shell ${currentIsRaining ? "weather-rain" : ""}`}>
      {currentIsRaining && (
        <div className="rain-layer" aria-hidden="true">
          {Array.from({ length: 60 }, (_, i) => (
            <span
              key={i}
              className="rain-streak"
              style={{
                left: `${(i * 29) % 100}%`,
                animationDelay: `${-((i * 13) % 28) / 10}s`,
                animationDuration: `${0.7 + ((i * 17) % 9) / 10}s`,
                opacity: 0.2 + ((i * 11) % 50) / 100,
              }}
            />
          ))}
        </div>
      )}

      <main className="dashboard">
        <header className="topbar">
          <div>
            <div className="eyebrow">DISASTER MANAGEMENT • NER</div>
            <h1>NER Landslide Early Warning System</h1>
            <p>Live rainfall, terrain intelligence, alerts and risk monitoring</p>
          </div>
          <div className="topbar-actions">
            <button className="ghost-btn" onClick={enableNotifications}>
              🔔 {notificationsEnabled ? "Alerts Enabled" : "Enable Alerts"}
            </button>
            <div className="live-chip"><span /> LIVE</div>
          </div>
        </header>

        {error && <div className="error-banner">⚠️ {error}</div>}

        <section className="control-panel">
          <div className="search-row">
            <div className="search-input-wrap">
              <span>⌕</span>
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && performSearch()}
                placeholder="Search city, district or monitoring point..."
              />
            </div>
            <button className="primary-btn" onClick={performSearch} disabled={busy}>
              {busy ? "Working…" : "Search"}
            </button>
            <button className="location-btn" onClick={useCurrentLocation} disabled={busy}>
              📍 Use My Location
            </button>
            {activeSource !== "default" && (
              <button className="mini-btn reset-btn" onClick={() => {
                setActiveSource("default");
                setSelectedCoordinate(null);
                setSelectedLocation(null);
                setSearchResults([]);
                setSearchQuery("");
                refreshDefault();
              }}>
                ↺ NER Focus
              </button>
            )}
          </div>
          {searchResults.length > 0 && (
            <div className="search-results">
              {searchResults.map((item) => (
                <button key={item.id} className="search-result" onClick={() => handleSearchResult(item)}>
                  <div>
                    <strong>📍 {item.location_name}</strong>
                    <small>{item.district}{item.state ? `, ${item.state}` : ""}</small>
                  </div>
                  <span>{item.latitude.toFixed(4)}, {item.longitude.toFixed(4)}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="hero-grid">
          <div className="selected-hero">
            <div className="hero-label">CURRENT MONITORING FOCUS</div>
            <h2>📍 {risk?.searched_place || risk?.location || "Loading…"}</h2>
            <p>{risk?.district}{risk?.district && risk?.state ? ", " : ""}{risk?.state}</p>
            <div className="coordinate-row">
              <span>LAT {Number(risk?.latitude || 0).toFixed(4)}</span>
              <span>LON {Number(risk?.longitude || 0).toFixed(4)}</span>
              <span>UPDATED {formatTime(risk?.recorded_at)}</span>
            </div>
          </div>

          <div className="hero-risk">
            <div>
              <div className="hero-label">RISK STATUS</div>
              <div className="risk-score-big">{risk?.risk_score ?? "—"}<small>/100</small></div>
            </div>
            <div className={riskClass(risk?.risk_level)}>{risk?.risk_level || "UNKNOWN"}</div>
          </div>
        </section>

        <section className="kpi-grid">
          <div className="kpi-card accent-green">
            <span>RAIN 24H</span>
            <strong>{risk?.rainfall_24h ?? 0}<small> mm</small></strong>
            <em>{risk?.rainfall_6h ?? 0} mm / 6h</em>
          </div>
          <div className="kpi-card accent-orange">
            <span>SLOPE</span>
            <strong>{risk?.slope_degree ?? 0}<small>°</small></strong>
            <em>{risk?.elevation_m ?? "—"} m elevation</em>
          </div>
          <div className="kpi-card accent-blue">
            <span>TEMPERATURE</span>
            <strong>{risk?.temperature ?? "—"}<small>°C</small></strong>
            <em>{risk?.precipitation_probability_max ?? 0}% rain probability</em>
          </div>
          <div className="kpi-card accent-cyan">
            <span>SOIL MOISTURE</span>
            <strong>{risk?.soil_moisture_0_7cm != null ? (risk.soil_moisture_0_7cm * 100).toFixed(0) : "—"}<small>%</small></strong>
            <em>0–7 cm model layer</em>
          </div>
          <div className="kpi-card accent-purple">
            <span>NEXT 6H RAIN</span>
            <strong>{risk?.forecast_rain_6h ?? 0}<small> mm</small></strong>
            <em>Forecast context</em>
          </div>
        </section>

        {(risk?.risk_level === "HIGH" || risk?.risk_level === "CRITICAL") && (
          <div className="danger-banner">
            <div className="danger-icon">!</div>
            <div>
              <strong>{risk.risk_level} RISK CONDITION DETECTED</strong>
              <p>Review live rainfall, terrain and field information before making operational decisions.</p>
            </div>
          </div>
        )}

        <section className="content-grid main-grid">
          <div className="panel map-panel">
            <div className="panel-head">
              <div>
                <div className="panel-kicker">GIS INTELLIGENCE</div>
                <h3>NER Live Risk Map</h3>
              </div>
              <div className="map-actions">
                <button className={satelliteEnabled ? "mini-btn active" : "mini-btn"} onClick={() => setSatelliteEnabled((v) => !v)}>
                  🛰 {satelliteEnabled ? "Satellite On" : "Satellite"}
                </button>
                <button className="mini-btn" onClick={refreshTerrain} disabled={terrainBusy}>
                  ⛰ {terrainBusy ? "Refreshing…" : "Refresh Terrain"}
                </button>
                <button className="mini-btn" onClick={exportLocations}>
                  ⇩ Export CSV
                </button>
              </div>
            </div>
            <div className="legend">
              {Object.entries(RISK_COLORS).map(([level, color]) => (
                <span key={level}><i style={{ background: color }} /> {level}</span>
              ))}
            </div>
            <div className="map-wrap">
              <MapView
                locations={locations}
                selectedLocation={selectedLocation}
                selectedCoordinate={selectedCoordinate}
                onMarkerSelect={selectMarker}
                onMapClick={handleMapClick}
                focusCoordinate={focusCoordinate}
                satelliteEnabled={satelliteEnabled}
              />
            </div>
            <p className="map-hint">Click a monitoring marker for details. Click any open area to calculate a coordinate-based live risk.</p>
          </div>

          <aside className="panel focus-panel">
            <div className="panel-kicker">LOCATION INTELLIGENCE</div>
            <h3>{selectedLocation?.location_name || risk?.searched_place || risk?.location || "Selected location"}</h3>
            <p className="muted">{selectedLocation ? `${selectedLocation.district}, ${selectedLocation.state}` : "Live risk details"}</p>
            <div className="focus-risk-row">
              <div className="focus-score">{selectedLocation?.risk_score ?? risk?.risk_score ?? "—"}<small>/100</small></div>
              <div className={riskClass(selectedLocation?.risk_level || risk?.risk_level)}>{selectedLocation?.risk_level || risk?.risk_level || "UNKNOWN"}</div>
            </div>
            <div className="metric-list">
              <div><span>Rainfall 24h</span><strong>{selectedLocation?.rainfall_24h ?? risk?.rainfall_24h ?? 0} mm</strong></div>
              <div><span>Slope</span><strong>{selectedLocation?.slope_degree ?? risk?.slope_degree ?? 0}°</strong></div>
              <div><span>Elevation</span><strong>{selectedLocation?.elevation_m ?? risk?.elevation_m ?? "—"} m</strong></div>
              <div><span>Temperature</span><strong>{selectedLocation?.temperature ?? risk?.temperature ?? "—"}°C</strong></div>
              <div><span>Rain score</span><strong>{selectedLocation?.rainfall_score ?? risk?.rainfall_score ?? 0}/100</strong></div>
              <div><span>Slope score</span><strong>{selectedLocation?.slope_score ?? risk?.slope_score ?? 0}/100</strong></div>
            </div>
            <div className="source-box">
              <span>Terrain source</span>
              <strong>{risk?.slope_source || "Stored terrain data"}</strong>
            </div>
          </aside>
        </section>

        <section className="content-grid secondary-grid">
          <div className="panel chart-panel">
            <div className="panel-head">
              <div>
                <div className="panel-kicker">TIME SERIES</div>
                <h3>Risk History</h3>
              </div>
              <span className="muted">Last {history.length || 0} records</span>
            </div>
            {history.length ? (
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history}>
                    <defs>
                      <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                    <XAxis dataKey="recorded_at" tickFormatter={formatTime} stroke="#64748b" />
                    <YAxis domain={[0, 100]} stroke="#64748b" />
                    <Tooltip labelFormatter={formatTime} />
                    <Area type="monotone" dataKey="risk_score" stroke="#38bdf8" fill="url(#riskFill)" strokeWidth={3} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="empty-state">📈 Risk history will populate as monitoring snapshots are collected.</div>
            )}
          </div>

          <div className="panel distribution-panel">
            <div className="panel-kicker">REGIONAL STATUS</div>
            <h3>Risk Distribution</h3>
            <div className="distribution-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={4}>
                    {pieData.map((entry) => <Cell key={entry.name} fill={RISK_COLORS[entry.name]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="distribution-center">
                <strong>{locations.length}</strong>
                <span>points</span>
              </div>
            </div>
            <div className="status-list">
              {Object.entries(counts).map(([level, count]) => (
                <div key={level}><span><i style={{ background: RISK_COLORS[level] }} />{level}</span><strong>{count}</strong></div>
              ))}
            </div>
          </div>
        </section>

        <section className="panel state-panel">
          <div className="panel-head">
            <div>
              <div className="panel-kicker">REGIONAL BREAKDOWN</div>
              <h3>State Risk Overview</h3>
            </div>
            <span className="muted">Latest stored risk snapshots</span>
          </div>
          {stateSummary.length ? (
            <div className="state-table-wrap">
              <table className="state-table">
                <thead>
                  <tr><th>State</th><th>Points</th><th>Avg risk</th><th>High/Critical</th></tr>
                </thead>
                <tbody>
                  {stateSummary.map((row) => (
                    <tr key={row.state}>
                      <td>{row.state}</td>
                      <td>{row.locations}</td>
                      <td>{row.avg_risk_score ?? "—"}</td>
                      <td>{row.high_or_critical}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state compact">State-level risk data will appear after live snapshots are stored.</div>
          )}
        </section>

        <section className="content-grid lower-grid">
          <div className="panel alerts-panel">
            <div className="panel-head">
              <div>
                <div className="panel-kicker">EARLY WARNING</div>
                <h3>Active Alerts</h3>
              </div>
              <span className="alert-count">{analytics?.active_alerts ?? alerts.length}</span>
            </div>
            {alerts.length ? (
              <div className="alert-list">
                {alerts.map((alert) => (
                  <div key={alert.id} className="alert-item">
                    <div className={`alert-level ${alert.risk_level.toLowerCase()}`}>{alert.risk_level}</div>
                    <div className="alert-content">
                      <strong>{alert.location_name || "Location"}</strong>
                      <p>{alert.message}</p>
                      <small>{formatTime(alert.created_at)}</small>
                    </div>
                    <button className="mini-btn" onClick={() => acknowledgeAlert(alert.id)}>Acknowledge</button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">✅ No active high/critical alerts.</div>
            )}
          </div>

          <div className="panel ai-panel">
            <div className="panel-kicker">AI / ML READINESS</div>
            <h3>Experimental Model</h3>
            <div className="ai-status">
              <span className={`status-dot ${modelStatus?.available ? "ready" : "pending"}`} />
              {modelStatus?.available ? "Model artifact available" : "Model not trained"}
            </div>
            <div className="ai-stats">
              <div><span>Labeled samples</span><strong>{modelStatus?.samples_available ?? 0}</strong></div>
              <div><span>Training ready</span><strong>{modelStatus?.ready_for_training ? "YES" : "NO"}</strong></div>
              <div><span>Minimum samples</span><strong>{modelStatus?.minimum_samples ?? 30}</strong></div>
            </div>
            {modelStatus?.metadata?.accuracy != null && (
              <div className="ai-metrics">
                <div><span>Accuracy</span><strong>{(modelStatus.metadata.accuracy * 100).toFixed(1)}%</strong></div>
                <div><span>F1</span><strong>{(modelStatus.metadata.f1 * 100).toFixed(1)}%</strong></div>
                <div><span>ROC-AUC</span><strong>{(modelStatus.metadata.roc_auc * 100).toFixed(1)}%</strong></div>
              </div>
            )}
            <p className="ai-note">The application keeps ML output separate from the live prototype risk index until representative historical labels and validation are available.</p>
            <button className="secondary-btn" onClick={async () => {
              try {
                const result = await apiPost("/api/ml/train");
                setModelStatus((prev) => ({ ...prev, available: true, metadata: result }));
              } catch (err) {
                setError(err.message || "Model training failed.");
              }
            }}>Train / Refresh Model</button>
          </div>
        </section>

        <footer className="footer-bar">
          <div><span>System status</span><strong>Operational</strong></div>
          <div><span>Monitoring points</span><strong>{locations.length}</strong></div>
          <div><span>Refresh cycle</span><strong>5 min</strong></div>
          <div><span>Last refresh</span><strong>{lastRefresh ? formatTime(lastRefresh) : "—"}</strong></div>
          <div><span>API</span><strong>{API_BASE.replace(/^https?:\/\//, "")}</strong></div>
        </footer>

        <div className="attribution-note">
          Weather/elevation data: Open-Meteo with Copernicus DEM attribution. Satellite context: NASA GIBS. Prototype risk thresholds require local validation.
        </div>
      </main>
    </div>
  );
}

export default App;
