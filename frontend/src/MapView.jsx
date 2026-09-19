import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import { useEffect } from "react";
import "leaflet/dist/leaflet.css";

function riskColor(level) {
  if (level === "CRITICAL") return "#991b1b";
  if (level === "HIGH") return "#ef4444";
  if (level === "MEDIUM") return "#f59e0b";
  if (level === "LOW") return "#22c55e";
  return "#94a3b8";
}

function FocusController({ focusCoordinate }) {
  const map = useMap();

  useEffect(() => {
    if (!focusCoordinate) return;
    map.flyTo(
      [focusCoordinate.latitude, focusCoordinate.longitude],
      Math.max(map.getZoom(), 8),
      { duration: 1.1 }
    );
  }, [focusCoordinate, map]);

  return null;
}

function ClickHandler({ onMapClick }) {
  useMapEvents({
    click(event) {
      onMapClick?.({
        latitude: event.latlng.lat,
        longitude: event.latlng.lng,
      });
    },
  });
  return null;
}

export default function MapView({
  locations,
  selectedLocation,
  onMarkerSelect,
  onMapClick,
  focusCoordinate,
  satelliteEnabled,
  selectedCoordinate,
}) {
  const satelliteDate = new Date(Date.now() - 2 * 86400000).toISOString().slice(0, 10);

  return (
    <MapContainer
      center={[25.5, 92.5]}
      zoom={6}
      scrollWheelZoom
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {satelliteEnabled && (
        <TileLayer
          url={
            `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/` +
            `MODIS_Terra_CorrectedReflectance_TrueColor/default/` +
            `${satelliteDate}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`
          }
          attribution="NASA GIBS / Earthdata"
          opacity={0.72}
          maxZoom={9}
        />
      )}

      <FocusController focusCoordinate={focusCoordinate} />
      <ClickHandler onMapClick={onMapClick} />

      {locations.map((location) => (
        <CircleMarker
          key={location.id}
          center={[location.latitude, location.longitude]}
          radius={
            selectedLocation?.id === location.id
              ? 15
              : location.risk_level === "CRITICAL"
                ? 14
                : location.risk_level === "HIGH"
                  ? 12
                  : location.risk_level === "MEDIUM"
                    ? 10
                    : 8
          }
          pathOptions={{
            color: riskColor(location.risk_level),
            fillColor: riskColor(location.risk_level),
            fillOpacity: 0.82,
            weight: selectedLocation?.id === location.id ? 4 : 2,
          }}
          eventHandlers={{
            click: () => onMarkerSelect?.(location),
          }}
        >
          <Popup>
            <div className="popup-title">📍 {location.location_name}</div>
            <div className="popup-meta">
              {location.district}, {location.state}
            </div>
            <div className="popup-grid">
              <span>Risk</span><strong>{location.risk_level}</strong>
              <span>Score</span><strong>{location.risk_score}/100</strong>
              <span>Rain 24h</span><strong>{location.rainfall_24h ?? 0} mm</strong>
              <span>Slope</span><strong>{location.slope_degree ?? 0}°</strong>
              <span>Temp</span><strong>{location.temperature ?? "—"}°C</strong>
            </div>
          </Popup>
        </CircleMarker>
      ))}

      {selectedCoordinate && (
        <CircleMarker
          center={[selectedCoordinate.latitude, selectedCoordinate.longitude]}
          radius={10}
          pathOptions={{
            color: "#38bdf8",
            fillColor: "#38bdf8",
            fillOpacity: 0.9,
            weight: 4,
          }}
        >
          <Popup>
            <strong>Selected coordinate</strong>
            <br />
            {selectedCoordinate.latitude.toFixed(5)}, {selectedCoordinate.longitude.toFixed(5)}
          </Popup>
        </CircleMarker>
      )}
    </MapContainer>
  );
}
