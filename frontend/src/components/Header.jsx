import { Brain, Sparkles } from "lucide-react";
import McpStatusPanel from "./McpStatusPanel.jsx";

export default function Header({ mcpStatus, health }) {
  return (
    <header className="site-header">
      <div className="brand">
        <div className="brand-icon" aria-hidden="true">
          <Sparkles size={24} />
        </div>
        <div>
          <p className="eyebrow">맛집 추천 AI Agent 웹 서비스</p>
          <h1>오늘 뭐 먹지 AI</h1>
          <p>지역, 날씨, 최근 먹은 메뉴와 취향을 분석해 오늘의 맛집을 추천합니다.</p>
        </div>
      </div>
      <div className="header-side">
        <McpStatusPanel status={mcpStatus} compact />
        <div className="mode-chip">
          <Brain size={16} aria-hidden="true" />
          <span>{health?.use_llm ? "LLM Agent 실행 중" : "LLM 없이 rule-based Agent 실행 중"}</span>
        </div>
      </div>
    </header>
  );
}
