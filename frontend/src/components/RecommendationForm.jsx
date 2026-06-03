import { Search } from "lucide-react";

const examples = [
  "대전 구암역 근처에서 파스타를 먹고 싶어",
  "양식 파스타 먹고싶어. 전북대 근처 가성비 있는 곳",
  "전주 객사 근처 친구랑 저녁 가성비 좋은 곳",
  "서울 홍대 초밥 리뷰 좋은 곳",
  "부산 해운대 카페 디저트",
  "제주 애월 파스타",
];

const weatherOptions = ["자동 조회", "맑음", "비", "흐림", "추움", "더움", "눈"];

export default function RecommendationForm({ form, setForm, onSubmit, loading }) {
  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  return (
    <form className="recommend-form" onSubmit={onSubmit}>
      <div className="form-section-title">
        <span>추천 조건 입력</span>
        <small>지역, 세부 위치, 메뉴/음식 종류를 자연어로 적으면 Agent가 조건을 해석합니다.</small>
      </div>

      <label className="field" htmlFor="natural-query">
        <span>자연어 요청</span>
        <textarea
          id="natural-query"
          value={form.natural_query}
          onChange={(event) => updateField("natural_query", event.target.value)}
          placeholder="예: 양식 파스타 먹고싶어. 전북대 근처 가성비 있는 곳"
          rows={4}
        />
      </label>

      <div className="chip-group" aria-label="예시 요청">
        {examples.map((example) => (
          <button type="button" className="chip" onClick={() => updateField("natural_query", example)} key={example}>
            {example}
          </button>
        ))}
      </div>

      <div className="field-grid">
        <label className="field" htmlFor="yesterday-menu">
          <span>어제 먹은 메뉴</span>
          <input
            id="yesterday-menu"
            value={form.yesterday_menu}
            onChange={(event) => updateField("yesterday_menu", event.target.value)}
            placeholder="예: 치킨, 피자, 김치찌개"
          />
        </label>
        <label className="field" htmlFor="today-menu">
          <span>오늘 먹은 메뉴</span>
          <input
            id="today-menu"
            value={form.today_menu}
            onChange={(event) => updateField("today_menu", event.target.value)}
            placeholder="예: 라면, 김밥, 돈까스"
          />
        </label>
      </div>

      <label className="field" htmlFor="weather">
        <span>날씨</span>
        <select id="weather" value={form.weatherOption} onChange={(event) => updateField("weatherOption", event.target.value)}>
          {weatherOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <button className="submit-button" type="submit" disabled={loading}>
        <Search size={18} aria-hidden="true" />
        {loading ? "Agent가 분석 중..." : "추천받기"}
      </button>
    </form>
  );
}
