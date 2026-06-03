const LABELS = {
  weather: "Weather MCP",
  restaurant: "Restaurant MCP",
  memory: "Memory MCP",
  place: "Place MCP",
};

export default function McpStatusPanel({ status, compact = false }) {
  const servers = status?.servers || {};
  const keys = ["weather", "restaurant", "memory", "place"];

  return (
    <div className={compact ? "mcp-status compact" : "mcp-status"}>
      {keys.map((key) => {
        const connected = servers[key]?.status === "connected";
        return (
          <div className="mcp-item" key={key}>
            <span className={connected ? "status-dot connected" : "status-dot failed"} aria-hidden="true" />
            <span>{LABELS[key]}</span>
            <small>{connected ? "연결됨" : "fallback 데이터로 동작 중"}</small>
          </div>
        );
      })}
    </div>
  );
}
