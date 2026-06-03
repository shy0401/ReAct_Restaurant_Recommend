# 제출 체크리스트

제출 전 아래 항목을 확인합니다.

## 1. 필수 제출 항목

- [x] 소스 코드 전체
- [x] `requirements.txt`
- [x] `README.md`
- [x] 실행 화면 또는 실행 로그
- [x] Agentic Design Pattern 설명 문서
- [x] ReAct Agent 도구 호출 Trace
- [x] 외부 API 사용 방법 문서
- [x] API Key 없이 fallback 데이터셋으로 실행 가능하다는 설명

## 2. 과제 요구사항 확인

- [x] 맛집 검색 도구 구현
- [x] 지역 기반 검색
- [x] 세부 위치 기반 검색
- [x] 음식 종류와 메뉴 키워드 기반 검색
- [x] 평점, 리뷰 수, 거리, 가격대 고려
- [x] 외부 API 또는 샘플 데이터셋 사용
- [x] ReAct Pattern 적용
- [x] Agentic Design Pattern 2개 이상 적용
- [x] ReAct Agent Client 실행 루프 구현
- [x] 존재하지 않는 지역 예외 처리
- [x] 검색 결과 없음 예외 처리
- [x] 음식 종류가 모호한 경우 warning 또는 Observation 기록
- [x] API 호출 실패 대응
- [x] 사용자 조건 부족 대응
- [x] 실행 테스트 시나리오와 Trace 제출
- [x] README, requirements, 실행 로그, 패턴 설명, API 설명 포함

## 3. 실행 검증 명령

백엔드 테스트:

```powershell
python -m pytest -q
```

과제 시나리오 Trace 생성:

```powershell
python scripts/run_submission_scenario.py
```

제출 zip 생성:

```powershell
python scripts/package_submission.py
```

프론트엔드 빌드:

```powershell
cd frontend
npm run build
cd ..
```

## 4. 최종 검증 결과

검증일: 2026-06-03

| 항목 | 결과 | 확인 내용 |
| --- | --- | --- |
| `git status --short` 시작 상태 | 통과 | 변경 사항 없음에서 시작 |
| `python -m pytest -q` | 통과 | `36 passed` |
| `python scripts/run_submission_scenario.py` | 통과 | Trace JSON/TXT/요약 md 생성 |
| `cd frontend && npm run build` | 통과 | `Frontend build completed: dist/` |
| `python scripts/package_submission.py` | 통과 | `신하윤_202112026_실습4.zip` 생성 |
| Trace 필수 항목 | 통과 | `Thought`, `Action`, `Action Input`, `Observation`, `Final Answer`, `Reflection` 포함 |
| Tool 이름 표시 | 통과 | `weather.get_weather`, `restaurant.search_restaurants`, `place.get_place_detail` 포함 |
| Reflection 결과 | 통과 | `approved=true`, `score=10` |
| 예외 처리 테스트 | 통과 | `tests/test_error_handling.py` 포함 |
| zip 금지 파일 검사 | 통과 | `.env`, `.venv`, `venv`, `__pycache__`, `node_modules`, zip 내부 API Key 없음 |

남은 주의사항:

- `submission_outputs/`는 `.gitignore` 대상이므로 Git 커밋에는 포함하지 않습니다.
- 제출 zip에는 생성된 Trace 파일과 zip 파일 자체가 들어가지만, 저장소 커밋에는 포함하지 않습니다.
- `.env`와 실제 API Key는 절대 제출 zip이나 Git 커밋에 넣지 않습니다.
- 실제 음식점 사진은 Google Places API Key가 없으면 fallback 이미지로 표시됩니다.

## 5. 과제 시나리오 기대 결과

입력:

```text
전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘.
```

확인:

- [x] `parsed_conditions.region == "전주"`
- [x] `parsed_conditions.area == "객사"`
- [x] `parsed_conditions.companion == "친구"`
- [x] `parsed_conditions.purpose == "저녁"`
- [x] `parsed_conditions.max_price == 15000`
- [x] `parsed_conditions.min_rating >= 4.0`
- [x] `parsed_conditions.min_review_count >= 50`
- [x] 최종 추천이 3곳 이상
- [x] 추천 3곳이 모두 전주
- [x] 최소 2곳 이상이 객사 또는 객리단길 관련
- [x] 추천 이유에 친구, 저녁, 가격/가성비, 리뷰/평점 조건 포함
- [x] Reflection 결과 포함
- [x] 다른 지역 후보로 억지 보강하지 않음

최종 추천 3곳:

1. 객사 소담전골
2. 객리단길 불고기식당
3. 전주객사 나베우동

## 6. 제출 zip에 포함할 파일

- [x] `app/`
- [x] `mcp_servers/`
- [x] `frontend/src/`
- [x] `frontend/public/`
- [x] `frontend/index.html`
- [x] `frontend/package.json`
- [x] `frontend/package-lock.json`
- [x] `frontend/scripts/`
- [x] `frontend/.env.example`
- [x] `ui/`
- [x] `scripts/run_submission_scenario.py`
- [x] `scripts/package_submission.py`
- [x] `tests/`
- [x] `README.md`
- [x] `requirements.txt`
- [x] `.env.example`
- [x] `docs/`
- [x] `submission_outputs/실행로그_trace.txt`
- [x] `submission_outputs/실행로그_trace.json`
- [x] `submission_outputs/과제_실행_요약.md`
- [x] 자동 생성된 `submission_outputs/신하윤_202112026_실습4.zip`

## 7. 제출 zip에서 제외할 파일

- [x] `.git/`
- [x] `.venv/`
- [x] `venv/`
- [x] `__pycache__/`
- [x] `.pytest_cache/`
- [x] `node_modules/`
- [x] `frontend/node_modules/`
- [x] `frontend/dist/`
- [x] `dist/`
- [x] `build/`
- [x] `.env`
- [x] API Key가 들어 있는 파일
- [x] `app/data/place_cache.json`
- [x] `app/data/meal_history.json`
- [x] IDE 설정 파일

## 8. 제출 파일명

권장 형식:

```text
[이름]_[학번]_실습4.zip
```

사용자 제출 파일명 예시:

```text
신하윤_202112026_실습4.zip
```

## 9. 최종 확인

- [x] README만 보고 설치와 실행이 가능한지 확인
- [x] Web UI에서 추천 결과, ReAct Trace, Reflection 결과를 확인할 수 있음
- [x] `/agent/run` 응답에 `submission_trace_text` 포함
- [x] `.env`와 API Key가 zip에 들어가지 않음
- [x] `docs/sample_submission_trace.txt`에 제출용 샘플 Trace 저장
