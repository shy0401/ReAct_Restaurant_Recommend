import { AlertCircle } from "lucide-react";

export default function ErrorBox({ message }) {
  if (!message) return null;

  return (
    <div className="error-box" role="alert">
      <AlertCircle size={20} aria-hidden="true" />
      <div>
        <strong>추천 결과를 불러오지 못했습니다.</strong>
        <p>{message}</p>
      </div>
    </div>
  );
}
