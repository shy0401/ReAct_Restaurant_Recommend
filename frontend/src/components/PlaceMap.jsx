import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function osmUrl(lat, lng) {
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=17/${lat}/${lng}`;
}

function loadKakaoMapScript(key) {
  if (window.kakao?.maps) return Promise.resolve(window.kakao);
  return new Promise((resolve, reject) => {
    const existing = document.querySelector("script[data-kakao-map='true']");
    if (existing) {
      existing.addEventListener("load", () => resolve(window.kakao));
      existing.addEventListener("error", reject);
      return;
    }
    const script = document.createElement("script");
    script.dataset.kakaoMap = "true";
    script.async = true;
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${key}&autoload=false`;
    script.onload = () => window.kakao.maps.load(() => resolve(window.kakao));
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

function KakaoMap({ latitude, longitude, name, onFail }) {
  const mapRef = useRef(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const key = import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY;
    if (!key || !mapRef.current) {
      setFailed(true);
      onFail?.();
      return;
    }
    let cancelled = false;
    loadKakaoMapScript(key)
      .then((kakao) => {
        if (cancelled || !mapRef.current) return;
        const center = new kakao.maps.LatLng(latitude, longitude);
        const map = new kakao.maps.Map(mapRef.current, { center, level: 3 });
        new kakao.maps.Marker({ map, position: center, title: name });
      })
      .catch(() => {
        setFailed(true);
        onFail?.();
      });
    return () => {
      cancelled = true;
    };
  }, [latitude, longitude, name, onFail]);

  if (failed) return null;
  return <div className="place-map kakao-map" ref={mapRef} aria-label={`${name} 카카오 지도`} />;
}

export default function PlaceMap({ latitude, longitude, name, address, mapUrl }) {
  const lat = toNumber(latitude);
  const lng = toNumber(longitude);
  const hasCoordinates = lat !== null && lng !== null;
  const provider = import.meta.env.VITE_MAP_PROVIDER || "leaflet";
  const kakaoKey = import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY;
  const link = useMemo(() => (hasCoordinates ? osmUrl(lat, lng) : mapUrl), [hasCoordinates, lat, lng, mapUrl]);
  const [kakaoFailed, setKakaoFailed] = useState(false);

  if (!hasCoordinates) {
    return (
      <div className="map-empty">
        <strong>지도 좌표가 없어 주소 링크만 제공합니다.</strong>
        {address && <span>{address}</span>}
        {link && (
          <a href={link} target="_blank" rel="noreferrer">
            지도에서 보기
          </a>
        )}
      </div>
    );
  }

  const useKakao = provider === "kakao" && kakaoKey && !kakaoFailed;

  return (
    <div className="place-map-wrap">
      {useKakao ? (
        <div onError={() => setKakaoFailed(true)}>
          <KakaoMap latitude={lat} longitude={lng} name={name} onFail={() => setKakaoFailed(true)} />
        </div>
      ) : (
        <MapContainer className="place-map" center={[lat, lng]} zoom={16} scrollWheelZoom={false}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Marker position={[lat, lng]}>
            <Popup>
              <strong>{name}</strong>
              {address && <p>{address}</p>}
            </Popup>
          </Marker>
        </MapContainer>
      )}
    </div>
  );
}
