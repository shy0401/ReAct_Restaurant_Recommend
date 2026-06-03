from __future__ import annotations

import os

import requests
import streamlit as st


API_URL = os.getenv("FOOD_AGENT_API_URL", "http://localhost:8000")

st.set_page_config(page_title="맛집 추천 AI Agent", page_icon="🍽️", layout="wide")
st.title("맛집 추천 AI Agent")

with st.form("recommend_form"):
    col1, col2 = st.columns(2)
    with col1:
        region = st.text_input("지역", value="전주")
        yesterday_menu = st.text_input("어제 먹은 메뉴", value="치킨")
        today_menu = st.text_input("오늘 먹은 메뉴", value="라면")
    with col2:
        preference = st.text_area("음식 선호도", value="따뜻한 한식, 국물 음식")
        use_manual_weather = st.checkbox("날씨 직접 입력")
        weather = st.selectbox("날씨", ["맑음", "비", "흐림", "추움", "더움"], disabled=not use_manual_weather)
    submitted = st.form_submit_button("추천받기", type="primary")

if submitted:
    payload = {
        "region": region,
        "yesterday_menu": yesterday_menu,
        "today_menu": today_menu,
        "weather": weather if use_manual_weather else None,
        "preference": preference,
    }
    try:
        response = requests.post(f"{API_URL}/recommend", json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        st.error(f"추천 API 호출 실패: {exc}")
        st.stop()

    weather_data = data["weather"]
    st.subheader("현재 날씨")
    w1, w2, w3 = st.columns(3)
    w1.metric("지역", weather_data.get("region"))
    w2.metric("날씨", weather_data.get("condition"))
    w3.metric("기온", "-" if weather_data.get("temperature") is None else f"{weather_data.get('temperature')}°C")
    st.info(weather_data.get("recommendation_hint", "날씨 힌트 없음"))

    st.subheader("최종 맛집 추천")
    for item in data["final_recommendations"]:
        with st.container(border=True):
            st.markdown(f"### {item['name']} · {item['score']}점")
            st.write(f"**대표 메뉴:** {', '.join(item['menu'])}")
            st.write(f"**지역/카테고리:** {item['region']} / {item['category']}")
            st.write(f"**추천 이유:** {item['reason']}")
            st.write(f"**날씨와의 관계:** {item['weather_relation']}")
            st.write(f"**최근 메뉴 중복 회피:** {item['recent_menu_relation']}")
            st.write(f"**선호도 반영:** {item['preference_relation']}")
            st.write(f"**가격대/평점:** {item['price_range']} / {item['rating']}")

    st.subheader("Reflection 검토")
    reflection = data["reflection"]
    st.success(reflection["summary"] if reflection["approved"] else reflection["improvement_instruction"])
    st.write(f"점수: {reflection['score']}/10")
    if reflection["issues"]:
        for issue in reflection["issues"]:
            st.warning(issue)
    else:
        st.write("발견된 문제 없음")

    with st.expander("ReAct Trace 보기"):
        for idx, step in enumerate(data["react_trace"], start=1):
            st.markdown(f"**Step {idx}**")
            st.code(f"Thought: {step['thought']}\nAction: {step['action']}\nAction Input: {step['action_input']}\nObservation: {step['observation']}")
