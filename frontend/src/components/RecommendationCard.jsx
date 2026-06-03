import { ExternalLink, Eye, MapPin, Star, WalletCards } from "lucide-react";
import { getApiBaseUrl } from "../api/recommendApi.js";

const fallbackImage = "/placeholders/default-restaurant.jpg";

function resolveImageUrl(url) {
  if (!url) return fallbackImage;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/places/photo")) return `${getApiBaseUrl()}${url}`;
  if (url.startsWith("/placeholders/")) return url;
  return url.startsWith("/") ? url : `/${url}`;
}

function isFallbackImage(item) {
  return item.thumbnail_is_fallback || item.thumbnail_source === "fallback" || item.thumbnail_url?.startsWith("/placeholders/");
}

export default function RecommendationCard({ item, rank, onQuickView }) {
  const score = Math.max(0, Math.min(100, Math.round(item.score || 0)));
  const imageUrl = resolveImageUrl(item.thumbnail_url || item.photos?.[0]?.url);
  const fallback = isFallbackImage(item);

  const openMap = () => {
    const latitude = Number(item.latitude);
    const longitude = Number(item.longitude);
    const fallbackMap = Number.isFinite(latitude) && Number.isFinite(longitude)
      ? `https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=17/${latitude}/${longitude}`
      : null;
    const url = item.map_url || item.place_url || fallbackMap;
    if (url) window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <article className={rank === 1 ? "recommend-card top-card" : "recommend-card"}>
      <div className="recommend-thumb">
        <img
          src={imageUrl}
          alt={`${item.name} 대표 이미지`}
          onError={(event) => {
            event.currentTarget.src = fallbackImage;
          }}
        />
        <span className="source-badge">{fallback ? "기본 이미지" : item.thumbnail_source}</span>
      </div>

      <div className="card-topline">
        <span className="rank-badge">{rank === 1 ? "오늘의 1순위 추천" : `${rank}위 추천`}</span>
        <div className="score-ring" style={{ "--score": `${score * 3.6}deg` }} aria-label={`추천 점수 ${score}점`}>
          <span>{score}</span>
        </div>
      </div>

      <h3>{item.name}</h3>
      <div className="meta-row">
        <span>
          <MapPin size={15} aria-hidden="true" />
          {item.region} · {item.category}
        </span>
        <span>
          <Star size={15} aria-hidden="true" />
          {item.rating}
        </span>
        <span>
          <WalletCards size={15} aria-hidden="true" />
          {item.price_range}
        </span>
      </div>

      {item.address && <p className="card-address">{item.address}</p>}
      {fallback && <p className="image-note">실제 사진 없음 · fallback 이미지 표시 중</p>}

      <div className="menu-list">
        {item.menu.map((menu) => (
          <span key={menu}>{menu}</span>
        ))}
      </div>

      <p className="reason">{item.reason}</p>

      <div className="explain-list">
        <p>
          <strong>날씨 매칭</strong>
          {item.weather_relation}
        </p>
        <p>
          <strong>최근 메뉴 회피</strong>
          {item.recent_menu_relation}
        </p>
        <p>
          <strong>선호도 반영</strong>
          {item.preference_relation}
        </p>
      </div>

      <div className="card-actions">
        <button type="button" className="outline-action" onClick={() => onQuickView(item)} disabled={!item.quick_view_available}>
          <Eye size={17} aria-hidden="true" />
          퀵뷰 보기
        </button>
        <button type="button" className="ghost-action" onClick={openMap}>
          <ExternalLink size={17} aria-hidden="true" />
          지도 보기
        </button>
      </div>
    </article>
  );
}
