# 제출 체크리스트

제출 전 아래 항목을 확인합니다.

## 1. 필수 제출 항목

- [ ] 소스 코드 전체
- [ ] `requirements.txt`
- [ ] `README.md`
- [ ] 실행 화면 또는 실행 로그
- [ ] Agentic Design Pattern 설명 문서
- [ ] ReAct Agent 도구 호출 Trace
- [ ] 외부 API 사용 방법 문서
- [ ] API Key 없이 fallback 데이터셋으로 실행 가능하다는 설명

## 2. 과제 요구사항 확인

- [ ] 맛집 검색 도구 구현
- [ ] 지역 기반 검색
- [ ] 세부 위치 기반 검색
- [ ] 음식 종류와 메뉴 키워드 기반 검색
- [ ] 평점, 리뷰 수, 거리, 가격대 고려
- [ ] 외부 API 또는 샘플 데이터셋 사용
- [ ] ReAct Pattern 적용
- [ ] Agentic Design Pattern 2개 이상 적용
- [ ] ReAct Agent Client 실행 루프 구현
- [ ] 존재하지 않는 지역 예외 처리
- [ ] 검색 결과 없음 예외 처리
- [ ] 음식 종류가 모호한 경우 warning 또는 Observation 기록
- [ ] API 호출 실패 대응
- [ ] 사용자 조건 부족 대응
- [ ] 실행 테스트 시나리오와 Trace 제출
- [ ] README, requirements, 실행 로그, 패턴 설명, API 설명 포함

## 3. 실행 검증 명령

백엔드 테스트:

```powershell
python -m pytest -q
```

과제 시나리오 Trace 생성:

```powershell
python scripts/run_submission_scenario.py
```

프론트엔드 빌드:

```powershell
cd frontend
npm run build
cd ..
```

## 4. 과제 시나리오 기대 결과

입력:

```text
전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘.
```

확인:

- [ ] `parsed_conditions.region == "전주"`
- [ ] `parsed_conditions.area == "객사"`
- [ ] `parsed_conditions.companion == "친구"`
- [ ] `parsed_conditions.purpose == "저녁"`
- [ ] `parsed_conditions.max_price == 15000`
- [ ] `parsed_conditions.min_rating >= 4.0`
- [ ] `parsed_conditions.min_review_count >= 50`
- [ ] 최종 추천이 3곳 이상
- [ ] 추천 3곳이 모두 전주
- [ ] 최소 2곳 이상이 객사 또는 객리단길 관련
- [ ] 추천 이유에 친구, 저녁, 가격/가성비, 리뷰/평점 조건 포함
- [ ] Reflection 결과 포함
- [ ] 다른 지역 후보로 억지 보강하지 않음

## 5. 제출 zip에 포함할 파일

- [ ] `app/`
- [ ] `mcp_servers/`
- [ ] `frontend/`
- [ ] `scripts/`
- [ ] `tests/`
- [ ] `docs/`
- [ ] `README.md`
- [ ] `requirements.txt`
- [ ] `.env.example`
- [ ] `frontend/.env.example`
- [ ] `.gitignore`
- [ ] 필요 시 `submission_outputs/실행로그_trace.txt`
- [ ] 필요 시 `submission_outputs/실행로그_trace.json`
- [ ] 필요 시 `submission_outputs/과제_실행_요약.md`

## 6. 제출 zip에서 제외할 파일

- [ ] `.venv/`
- [ ] `venv/`
- [ ] `__pycache__/`
- [ ] `.pytest_cache/`
- [ ] `node_modules/`
- [ ] `frontend/node_modules/`
- [ ] `frontend/dist/`
- [ ] `.env`
- [ ] API Key가 들어 있는 파일
- [ ] `app/data/place_cache.json`
- [ ] IDE 설정 파일

## 7. 제출 파일명

권장 형식:

```text
[이름]_[학번]_실습4.zip
```

사용자 제출 파일명 예시:

```text
신하윤_202112026_실습4.zip
```

## 8. 최종 확인

- [ ] README만 보고 설치와 실행이 가능한지 확인
- [ ] Web UI에서 추천 결과, ReAct Trace, Reflection 결과가 보이는지 확인
- [ ] `/agent/run` 응답에 `submission_trace_text`가 포함되는지 확인
- [ ] `.env`와 API Key가 zip에 들어가지 않았는지 확인
- [ ] zip을 새 폴더에 풀어 실행 명령을 다시 확인
