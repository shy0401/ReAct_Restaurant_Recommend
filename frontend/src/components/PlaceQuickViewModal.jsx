import { ChevronLeft, ChevronRight, ExternalLink, MapPin, Phone, Star, X } from "lucide-react";
import { useEffect, useState } from "react";
import { getApiBaseUrl } from "../api/recommendApi.js";
import PlaceMap from "./PlaceMap.jsx";

const fallbackImage = "/placeholders/default-restaurant.jpg";

function resolveImageUrl(url) {
  if (!url) return fallbackImage;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/places/photo")) return `${getApiBaseUrl()}${url}`;
  if (url.startsWith("/placeholders/")) return url;
  return url.startsWith("/") ? url : `/${url}`;
}

function isFallbackPhoto(photo) {
  return photo?.is_fallback || photo?.source === "fallback" || photo?.url?.startsWith("/placeholders/");
}

export default function PlaceQuickViewModal({ open, loading, data, error, onClose }) {
  const [photoIndex, setPhotoIndex] = useState(0);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  useEffect(() => {
    setPhotoIndex(0);
  }, [data?.place?.id, open]);

  if (!open) return null;

  const place = data?.place;
  const photos = data?.photos?.length
    ? data.photos
    : [{ url: fallbackImage, alt: "기본 맛집 이미지", source: "fallback", is_fallback: true }];
  const currentPhoto = photos[photoIndex] || photos[0];
  const map = data?.map || {};
  const mapUrl = map.map_url || place?.map_url;
  const directionsUrl = map.directions_url;
  const photoIsFallback = isFallbackPhoto(currentPhoto);

  const nextPhoto = () => setPhotoIndex((value) => (value + 1) % photos.length);
  const prevPhoto = () => setPhotoIndex((value) => (value - 1 + photos.length) % photos.length);

  return (
    <div className="modal-overlay" onMouseDown={onClose} role="presentation">
      <section className="quick-modal" role="dialog" aria-modal="true" aria-labelledby="quick-view-title" onMouseDown={(event) => event.stopPropagation()}>
        <button className="modal-close" type="button" onClick={onClose} aria-label="퀵뷰 닫기">
          <X size={22} />
        </button>

        {loading && (
          <div className="quick-skeleton">
            <div className="skeleton-photo" />
            <div className="skeleton-line wide" />
            <div className="skeleton-line" />
            <div className="skeleton-line short" />
          </div>
        )}

        {!loading && error && (
          <div className="quick-error">
            <h2>상세 정보를 불러오지 못했습니다.</h2>
            <p>{error}</p>
          </div>
        )}

        {!loading && place && (
          <>
            <div className="quick-photo">
              <img
                src={resolveImageUrl(currentPhoto.url)}
                alt={currentPhoto.alt || `${place.name} 대표 사진`}
                onError={(event) => {
                  event.currentTarget.src = fallbackImage;
                }}
              />
              <span className="source-badge">{photoIsFallback ? "기본 이미지" : currentPhoto.source}</span>
              {photos.length > 1 && (
                <div className="photo-controls">
                  <button type="button" onClick={prevPhoto} aria-label="이전 사진">
                    <ChevronLeft size={18} />
                  </button>
                  <button type="button" onClick={nextPhoto} aria-label="다음 사진">
                    <ChevronRight size={18} />
                  </button>
                </div>
              )}
            </div>

            <div className="quick-content">
              <div className="quick-title-row">
                <div>
                  <p className="eyebrow">맛집 상세 퀵뷰</p>
                  <h2 id="quick-view-title">{place.name}</h2>
                  <p>{place.category} · {place.region}</p>
                </div>
                <span className="data-source">{data.source === "fallback" || data.source === "fallback_sample" ? "샘플 상세 정보" : data.source}</span>
              </div>

              <div className="quick-meta-grid">
                <span><Star size={16} aria-hidden="true" /> 평점 {place.rating ?? "정보 없음"} · 리뷰 {place.review_count ?? 0}개</span>
                <span><Phone size={16} aria-hidden="true" /> {place.phone || "전화번호 정보 없음"}</span>
                <span><MapPin size={16} aria-hidden="true" /> {place.distance || "거리 정보 없음"}</span>
                <span>{place.price_range || "가격대 정보 없음"}</span>
              </div>

              <div className="quick-section">
                <h3>영업 정보</h3>
                <p>{place.opening_hours || "영업시간 정보 없음"}</p>
                <p>{place.road_address || place.address || "주소 정보 없음"}</p>
              </div>

              {(photoIsFallback || place.fallback_messages?.length > 0) && (
                <div className="fallback-note">
                  {photoIsFallback && <span>실제 음식점 사진 API 키가 없거나 사진 결과가 없어 기본 이미지를 표시합니다.</span>}
                  {place.fallback_messages?.map((message) => (
                    <span key={message}>{message}</span>
                  ))}
                </div>
              )}

              {!photoIsFallback && currentPhoto.attributions?.length > 0 && (
                <div className="photo-attribution" dangerouslySetInnerHTML={{ __html: currentPhoto.attributions.join(" ") }} />
              )}

              <div className="quick-section">
                <h3>대표 메뉴</h3>
                <div className="menu-cards">
                  {(data.menus || []).map((menu) => (
                    <article key={menu.name} className="menu-card">
                      <div>
                        <strong>{menu.name}</strong>
                        {menu.is_recommended && <span>추천 메뉴</span>}
                      </div>
                      <p>{menu.description || "메뉴 설명 정보 없음"}</p>
                      <em>{menu.price || "가격 정보 없음"}</em>
                    </article>
                  ))}
                </div>
              </div>

              <div className="quick-section">
                <h3>지도 위치</h3>
                <PlaceMap
                  latitude={map.latitude ?? place.latitude}
                  longitude={map.longitude ?? place.longitude}
                  name={place.name}
                  address={place.road_address || place.address}
                  mapUrl={mapUrl}
                />
                <div className="map-actions">
                  {mapUrl && (
                    <a href={mapUrl} target="_blank" rel="noreferrer">
                      <ExternalLink size={16} aria-hidden="true" />
                      지도에서 보기
                    </a>
                  )}
                  {directionsUrl && (
                    <a href={directionsUrl} target="_blank" rel="noreferrer">
                      <MapPin size={16} aria-hidden="true" />
                      길찾기
                    </a>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
