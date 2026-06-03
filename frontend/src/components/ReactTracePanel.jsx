import { ChevronDown } from "lucide-react";
import { useState } from "react";

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function traceText(trace) {
  return trace
    .map(
      (step, index) => `Step ${index + 1}
Thought
${step.thought}
Action
${step.action}
Action Input
${pretty(step.action_input)}
Observation
${pretty(step.observation)}`
    )
    .join("\n\n");
}

export default function ReactTracePanel({ trace = [] }) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState({});
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const text = traceText(trace);
    await navigator.clipboard?.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  const handleDownload = () => {
    const blob = new Blob([traceText(trace)], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "submission_react_trace.txt";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="trace-panel">
      <div className="trace-toolbar">
        <button className="panel-toggle" type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
          <div>
            <h2>AI Agent 추론 과정 보기</h2>
            <p>ReAct 기반으로 MCP 도구를 호출해 추천했습니다. 총 {trace.length}단계 실행</p>
          </div>
          <ChevronDown className={open ? "rotate" : ""} size={22} aria-hidden="true" />
        </button>
        <div className="trace-actions">
          <button className="text-button" type="button" onClick={handleCopy} disabled={!trace.length}>
            {copied ? "복사됨" : "Trace 복사"}
          </button>
          <button className="text-button" type="button" onClick={handleDownload} disabled={!trace.length}>
            제출 로그 다운로드
          </button>
        </div>
      </div>

      {open && (
        <div className="trace-list">
          {trace.map((step, index) => {
            const key = `${index}-${step.action}`;
            const observation = pretty(step.observation);
            const collapsed = observation.length > 520 && !expanded[key];
            return (
              <article className="trace-step" key={key}>
                <span className="step-label">Step {index + 1}</span>
                <div className="trace-block thought">
                  <strong>Thought</strong>
                  <p>{step.thought}</p>
                </div>
                <div className="trace-block action">
                  <strong>Action</strong>
                  <code>{step.action}</code>
                </div>
                <div className="trace-block">
                  <strong>Action Input</strong>
                  <pre>{pretty(step.action_input)}</pre>
                </div>
                <div className="trace-block observation">
                  <strong>Observation</strong>
                  <pre>{collapsed ? `${observation.slice(0, 520)}\n...` : observation}</pre>
                  {observation.length > 520 && (
                    <button className="text-button" type="button" onClick={() => setExpanded((current) => ({ ...current, [key]: !current[key] }))}>
                      {expanded[key] ? "접기" : "전체 보기"}
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
