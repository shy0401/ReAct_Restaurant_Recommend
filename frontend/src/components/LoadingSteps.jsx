const steps = ["입력 분석", "Weather MCP 호출", "Memory MCP 호출", "Restaurant MCP 호출", "ReAct 추론", "Reflection 검토", "최종 추천 생성"];

export default function LoadingSteps() {
  return (
    <div className="loading-card" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <div>
        <h3>MCP 서버에서 정보를 가져오는 중...</h3>
        <p>ReAct Agent가 추천 후보를 분석하고 Reflection으로 결과를 검토하고 있습니다.</p>
      </div>
      <ol className="loading-steps">
        {steps.map((step, index) => (
          <li key={step} style={{ animationDelay: `${index * 0.08}s` }}>
            <span>{index + 1}</span>
            {step}
          </li>
        ))}
      </ol>
    </div>
  );
}
