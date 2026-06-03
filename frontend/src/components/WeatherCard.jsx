import { CloudSun, Droplets, Thermometer } from "lucide-react";

const icons = {
  맑음: "☀️",
  비: "🌧️",
  흐림: "☁️",
  추움: "❄️",
  더움: "🔥",
  눈: "🌨️",
};

export default function WeatherCard({ weather }) {
  if (!weather) return null;
  const condition = weather.condition || "자동 조회";

  return (
    <section className="weather-card">
      <div className="weather-icon" aria-hidden="true">
        {icons[condition] || "🍽️"}
      </div>
      <div>
        <p className="eyebrow">{weather.region} 현재 날씨</p>
        <h2>{condition}</h2>
        <div className="weather-meta">
          <span>
            <Thermometer size={16} aria-hidden="true" />
            {weather.temperature === null || weather.temperature === undefined ? "기온 정보 없음" : `${weather.temperature}도`}
          </span>
          <span>
            <Droplets size={16} aria-hidden="true" />
            {weather.humidity === null || weather.humidity === undefined ? "습도 정보 없음" : `습도 ${weather.humidity}%`}
          </span>
          <span>
            <CloudSun size={16} aria-hidden="true" />
            {weather.source === "user_input" ? "직접 입력" : "MCP 조회"}
          </span>
        </div>
        <p className="weather-hint">{weather.recommendation_hint}</p>
      </div>
    </section>
  );
}
