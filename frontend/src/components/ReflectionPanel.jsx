import { CheckCircle2, RotateCcw } from "lucide-react";

export default function ReflectionPanel({ reflection }) {
  if (!reflection) return null;

  return (
    <section className="reflection-panel">
      <div className="reflection-header">
        <div>
          <p className="eyebrow">Reflection 검토 결과</p>
          <h2>{reflection.score}/10</h2>
        </div>
        <span className={reflection.approved ? "approval approved" : "approval improved"}>
          {reflection.approved ? <CheckCircle2 size={18} aria-hidden="true" /> : <RotateCcw size={18} aria-hidden="true" />}
          {reflection.approved ? "승인됨" : "개선 반영"}
        </span>
      </div>

      <p className="reflection-summary">{reflection.summary}</p>

      <div className="reflection-grid">
        <div>
          <h3>발견된 문제</h3>
          {reflection.issues?.length ? (
            <ul>
              {reflection.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          ) : (
            <p>발견된 문제 없음</p>
          )}
        </div>
        <div>
          <h3>개선 방향</h3>
          <p>{reflection.improvement_instruction}</p>
          <h3>검토 항목</h3>
          <ul>
            {(reflection.checked_items || []).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <h3>최종 추천에 반영된 내용</h3>
          <ul>
            {(reflection.final_changes || []).map((change) => (
              <li key={change}>{change}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
