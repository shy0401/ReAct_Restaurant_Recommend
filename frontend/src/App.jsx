import { useEffect, useState } from "react";
import { getHealth, getMcpStatus, getPlaceQuickView, runAgentQuery } from "./api/recommendApi.js";
import ErrorBox from "./components/ErrorBox.jsx";
import Header from "./components/Header.jsx";
import LoadingSteps from "./components/LoadingSteps.jsx";
import McpStatusPanel from "./components/McpStatusPanel.jsx";
import PlaceQuickViewModal from "./components/PlaceQuickViewModal.jsx";
import ReactTracePanel from "./components/ReactTracePanel.jsx";
import RecommendationCard from "./components/RecommendationCard.jsx";
import RecommendationForm from "./components/RecommendationForm.jsx";
import ReflectionPanel from "./components/ReflectionPanel.jsx";
import WeatherCard from "./components/WeatherCard.jsx";

const initialForm = {
  natural_query: "양식 파스타 먹고싶어. 전북대 근처 가성비 있는 곳",
  yesterday_menu: "",
  today_menu: "",
  weatherOption: "자동 조회",
};

function friendlyError(error) {
  if (!navigator.onLine) return "네트워크 연결을 확인해주세요.";
  if (String(error?.message || "").includes("Failed to fetch")) {
    return "백엔드 API 서버가 실행 중인지 확인해주세요. MCP 오류가 있어도 fallback 데이터로 추천을 계속하도록 구성되어 있습니다.";
  }
  return "추천 결과를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.";
}

function conditionValue(value) {
  return value || "조건 없음";
}

export default function App() {
  const [form, setForm] = useState(initialForm);
  const [mcpStatus, setMcpStatus] = useState(null);
  const [health, setHealth] = useState(null);
  const [result, setResult] = useState(null);
  const [parsedConditions, setParsedConditions] = useState(null);
  const [quickViewOpen, setQuickViewOpen] = useState(false);
  const [quickViewData, setQuickViewData] = useState(null);
  const [quickViewLoading, setQuickViewLoading] = useState(false);
  const [quickViewError, setQuickViewError] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("현재는 LLM 없이 rule-based Agent로 실행 중입니다.");

  useEffect(() => {
    Promise.allSettled([getMcpStatus(), getHealth()]).then(([mcp, apiHealth]) => {
      if (mcp.status === "fulfilled") setMcpStatus(mcp.value);
      if (apiHealth.status === "fulfilled") {
        setHealth(apiHealth.value);
        setNotice(apiHealth.value.use_llm ? "OPENAI_API_KEY 기반 LLM Agent 모드로 실행 중입니다." : "현재는 LLM 없이 rule-based Agent로 실행 중입니다.");
      }
    });
  }, []);

  const hasResult = Boolean(result?.final_recommendations?.length);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (!form.natural_query.trim()) {
      setError("원하는 지역과 메뉴를 자연어로 입력해주세요. 예: 전북대 근처 파스타 가성비 좋은 곳");
      return;
    }

    if (!form.yesterday_menu.trim() && !form.today_menu.trim()) {
      setNotice("최근 먹은 메뉴를 입력하면 더 정확하게 중복을 피할 수 있습니다.");
    }

    setLoading(true);
    try {
      const data = await runAgentQuery({
        query: form.natural_query.trim(),
        yesterday_menu: form.yesterday_menu.trim() || "입력 없음",
        today_menu: form.today_menu.trim() || "입력 없음",
        weather: form.weatherOption === "자동 조회" ? null : form.weatherOption,
      });
      setParsedConditions(data.parsed_conditions);
      setResult(data.result);
      if (!data.result?.final_recommendations?.length) {
        setNotice("조건을 엄격히 지키기 위해 무관한 음식으로 채우지 않았습니다. 조건을 조금 넓히면 더 많은 후보를 볼 수 있습니다.");
      }
      const refreshedStatus = await getMcpStatus().catch(() => null);
      if (refreshedStatus) setMcpStatus(refreshedStatus);
    } catch (submitError) {
      setError(friendlyError(submitError));
    } finally {
      setLoading(false);
    }
  };

  const openQuickView = async (item) => {
    setQuickViewOpen(true);
    setQuickViewLoading(true);
    setQuickViewError("");
    setQuickViewData(null);
    try {
      const data = await getPlaceQuickView({
        place_id: item.place_id || item.id,
        name: item.name,
        region: item.region,
      });
      setQuickViewData(data);
    } catch {
      setQuickViewError("장소 상세 정보를 가져오지 못했습니다. API 키가 없으면 fallback 상세 정보로 동작합니다.");
    } finally {
      setQuickViewLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <Header mcpStatus={mcpStatus} health={health} />

      <main className="page-grid">
        <aside className="left-column">
          <section className="hero-card">
            <div className="hero-pattern" aria-hidden="true">
              🍽️
            </div>
            <p className="eyebrow">MCP · ReAct · Reflection</p>
            <h2>오늘 뭐 먹을지 고민된다면?</h2>
            <p>지역, 세부 위치, 원하는 메뉴와 가격 조건을 우선 반영하고 날씨와 최근 식사는 보조 조건으로 분석합니다.</p>
            <div className="badge-row">
              <span>MCP 기반</span>
              <span>ReAct Trace</span>
              <span>Reflection 검토</span>
              <span>LLM 없이 실행 가능</span>
            </div>
          </section>

          <RecommendationForm form={form} setForm={setForm} onSubmit={handleSubmit} loading={loading} />

          <section className="side-card">
            <div className="form-section-title">
              <span>MCP 서버 상태</span>
              <small>일부 서버 연결 실패 시 fallback 데이터로 추천을 계속합니다.</small>
            </div>
            <McpStatusPanel status={mcpStatus} />
            <p className="llm-note">{notice}</p>
          </section>
        </aside>

        <section className="result-column">
          <ErrorBox message={error} />
          {loading && <LoadingSteps />}

          {!loading && !hasResult && (
            <section className="empty-state">
              <div aria-hidden="true">🍜</div>
              <h2>추천 결과가 여기에 표시됩니다</h2>
              <p>예시 문장을 눌러 바로 시연하거나 원하는 지역과 메뉴를 직접 입력해보세요.</p>
            </section>
          )}

          {hasResult && (
            <>
              <WeatherCard weather={result.weather} />

              {parsedConditions && (
                <section className="side-card">
                  <div className="form-section-title">
                    <span>해석된 조건</span>
                    <small>지역과 메뉴/음식 종류가 날씨보다 우선 적용됩니다.</small>
                  </div>
                  <div className="badge-row">
                    <span>지역: {conditionValue(parsedConditions.region)}</span>
                    <span>도시: {conditionValue(parsedConditions.city)}</span>
                    <span>구/군: {conditionValue(parsedConditions.district)}</span>
                    <span>세부 위치: {conditionValue(parsedConditions.area)}</span>
                    <span>랜드마크: {conditionValue(parsedConditions.landmark)}</span>
                    <span>음식 종류: {conditionValue(parsedConditions.food_type)}</span>
                    <span>메뉴: {conditionValue(parsedConditions.menu_keyword)}</span>
                    <span>가격: {parsedConditions.max_price ? `${parsedConditions.max_price.toLocaleString()}원 이하` : "조건 없음"}</span>
                    <span>위치 출처: {conditionValue(parsedConditions.location_source)}</span>
                    <span>신뢰도: {parsedConditions.location_confidence ? Math.round(parsedConditions.location_confidence * 100) + "%" : "조건 없음"}</span>
                  </div>
                </section>
              )}

              <div className="result-heading">
                <div>
                  <p className="eyebrow">오늘의 추천</p>
                  <h2>최종 맛집 추천 {result.final_recommendations.length}곳</h2>
                </div>
                <span>{result.input.region} · {result.input.preference}</span>
              </div>

              <div className="recommend-grid">
                {result.final_recommendations.map((item, index) => (
                  <RecommendationCard item={item} rank={index + 1} key={item.id} onQuickView={openQuickView} />
                ))}
              </div>

              <ReflectionPanel reflection={result.reflection} />
              <ReactTracePanel trace={result.react_trace} />
            </>
          )}
        </section>
      </main>
      <PlaceQuickViewModal
        open={quickViewOpen}
        loading={quickViewLoading}
        data={quickViewData}
        error={quickViewError}
        onClose={() => setQuickViewOpen(false)}
      />
    </div>
  );
}
