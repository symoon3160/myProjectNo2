from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import uuid4

import pandas as pd
import streamlit as st

from sheets_store import (
    StorageConfigurationError,
    add_activity,
    add_employee,
    add_goal,
    initialize_storage,
    load_all,
)


st.set_page_config(
    page_title="Growlog | 자기개발 대시보드",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)


STATUS_LABEL = {
    "in_progress": "진행 중",
    "completed": "완료",
    "on_hold": "보류",
    "cancelled": "취소",
}

CATEGORY_COLORS = {
    "기술": "#5667FF",
    "리더십": "#9B6BFF",
    "외국어": "#13A38B",
    "자격증": "#F09B3D",
    "독서": "#E65B7A",
    "기타": "#718096",
}


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"] { font-family: "Noto Sans KR", sans-serif; }
        .stApp { background: #F6F7FB; color: #1F2937; }
        [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E8EAF0; }
        [data-testid="stMetric"] {
            background: white;
            border: 1px solid #ECEEF4;
            padding: 18px 20px;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(27, 36, 59, 0.04);
        }
        [data-testid="stMetricLabel"] { color: #6B7280; }
        [data-testid="stMetricValue"] { color: #111827; font-weight: 800; }
        div[data-testid="stForm"] {
            background: white;
            border: 1px solid #E8EAF0;
            border-radius: 18px;
            padding: 20px;
        }
        .block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1440px; }
        .hero {
            background: linear-gradient(125deg, #2636B8 0%, #5667FF 55%, #8175FF 100%);
            border-radius: 24px;
            padding: 28px 32px;
            color: white;
            margin-bottom: 24px;
            box-shadow: 0 14px 35px rgba(65, 78, 200, 0.22);
        }
        .hero h1 { font-size: 30px; margin: 0 0 8px 0; }
        .hero p { margin: 0; opacity: 0.88; font-size: 15px; }
        .section-title { font-size: 19px; font-weight: 800; margin: 22px 0 12px 0; }
        .eyebrow {
            color: #5667FF; font-weight: 800; font-size: 12px;
            letter-spacing: .08em; text-transform: uppercase; margin-bottom: 4px;
        }
        .goal-card {
            background: white;
            border: 1px solid #E8EAF0;
            border-radius: 18px;
            padding: 18px 20px;
            margin-bottom: 12px;
            box-shadow: 0 8px 20px rgba(27, 36, 59, 0.035);
        }
        .goal-card h4 { margin: 0 0 6px 0; font-size: 16px; }
        .goal-meta { color: #7A8192; font-size: 13px; margin-bottom: 13px; }
        .progress-track { height: 9px; background: #EEF0F6; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; border-radius: 10px; }
        .progress-label {
            display: flex; justify-content: space-between; margin-top: 8px;
            color: #626A7A; font-size: 12px;
        }
        .notice {
            background: #FFF9EA; border: 1px solid #F6DF9B; border-radius: 14px;
            padding: 13px 15px; margin-bottom: 9px; color: #755A10; font-size: 14px;
        }
        .success-note {
            background: #EDFBF7; border: 1px solid #BFE9DD; border-radius: 14px;
            padding: 13px 15px; color: #14735F; font-size: 14px;
        }
        .small-muted { color: #7A8192; font-size: 13px; }
        .stButton > button, .stDownloadButton > button {
            border-radius: 10px; min-height: 40px; font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def quarter_range(today: date) -> tuple[date, date, str]:
    quarter = (today.month - 1) // 3 + 1
    start_month = (quarter - 1) * 3 + 1
    start = date(today.year, start_month, 1)
    if quarter == 4:
        end = date(today.year, 12, 31)
    else:
        end = date(today.year, start_month + 3, 1) - timedelta(days=1)
    return start, end, f"{today.year} Q{quarter}"


def refresh_data() -> None:
    employees, goals, activities = load_all()
    st.session_state.employees = employees
    st.session_state.goals = goals
    st.session_state.activities = activities


def initialize_state() -> None:
    initialize_storage()
    refresh_data()
    if st.session_state.employees.empty:
        st.session_state.current_employee_id = None
    elif "current_employee_id" not in st.session_state:
        st.session_state.current_employee_id = st.session_state.employees.iloc[0][
            "employee_id"
        ]
    elif st.session_state.current_employee_id not in set(
        st.session_state.employees["employee_id"]
    ):
        st.session_state.current_employee_id = st.session_state.employees.iloc[0][
            "employee_id"
        ]


def fmt_hours(value: float) -> str:
    return f"{value:,.1f}시간"


def progress_for_goal(goal_id: str) -> tuple[float, float]:
    goals = st.session_state.goals
    activities = st.session_state.activities
    goal = goals.loc[goals["goal_id"] == goal_id].iloc[0]
    actual = activities.loc[activities["goal_id"] == goal_id, "hours"].sum()
    planned = float(goal["planned_hours"])
    return float(actual), min(actual / planned * 100, 100.0) if planned else 0.0


def expected_progress(goal: pd.Series) -> float:
    today = date.today()
    start = pd.to_datetime(goal["start_date"]).date()
    end = pd.to_datetime(goal["end_date"]).date()
    total = max((end - start).days, 1)
    elapsed = min(max((today - start).days, 0), total)
    return elapsed / total * 100


def hero(title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{title}</h1>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_row(planned: float, actual: float, completed: int, extra_label: str, extra: str) -> None:
    rate = actual / planned * 100 if planned else 0
    cols = st.columns(4)
    cols[0].metric("계획 시간", fmt_hours(planned))
    cols[1].metric("수행 시간", fmt_hours(actual), f"{rate:.0f}% 달성")
    cols[2].metric("완료 목표", f"{completed}개")
    cols[3].metric(extra_label, extra)


def goal_cards(goals: pd.DataFrame) -> None:
    if goals.empty:
        st.info("등록된 목표가 없습니다. 새 목표를 만들어 학습 여정을 시작해보세요.")
        return

    for _, goal in goals.iterrows():
        actual, progress = progress_for_goal(goal["goal_id"])
        color = CATEGORY_COLORS.get(goal["category"], "#5667FF")
        end_date = pd.to_datetime(goal["end_date"]).date()
        remaining = (end_date - date.today()).days
        remaining_text = f"D-{remaining}" if remaining >= 0 else "기간 종료"
        st.markdown(
            f"""
            <div class="goal-card">
                <div class="eyebrow">{goal['category']} · {STATUS_LABEL.get(goal['status'], goal['status'])}</div>
                <h4>{goal['title']}</h4>
                <div class="goal-meta">{remaining_text} · {actual:.1f} / {goal['planned_hours']:.1f}시간</div>
                <div class="progress-track">
                    <div class="progress-fill" style="width:{progress:.1f}%; background:{color};"></div>
                </div>
                <div class="progress-label"><span>계획 대비 수행</span><strong>{progress:.0f}%</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def weekly_chart(activities: pd.DataFrame, planned_hours: float) -> None:
    q_start, q_end, _ = quarter_range(date.today())
    weeks = pd.date_range(q_start, q_end, freq="W-MON")
    if len(weeks) == 0:
        return
    chart = pd.DataFrame({"주차": weeks})
    per_week = planned_hours / len(weeks) if weeks.size else 0
    chart["주간 계획"] = per_week

    if activities.empty:
        chart["실제 수행"] = 0.0
    else:
        work = activities.copy()
        work["activity_date"] = pd.to_datetime(work["activity_date"])
        work["주차"] = work["activity_date"] - pd.to_timedelta(work["activity_date"].dt.weekday, unit="D")
        weekly = work.groupby("주차", as_index=False)["hours"].sum()
        chart = chart.merge(weekly, on="주차", how="left")
        chart["실제 수행"] = chart["hours"].fillna(0)
        chart = chart.drop(columns=["hours"])

    chart = chart.set_index("주차")
    st.line_chart(chart[["주간 계획", "실제 수행"]], color=["#A8B0C7", "#5667FF"])


def individual_dashboard(employee_id: str) -> None:
    employees = st.session_state.employees
    goals = st.session_state.goals
    activities = st.session_state.activities
    employee = employees.loc[employees["employee_id"] == employee_id].iloc[0]
    my_goals = goals[goals["employee_id"] == employee_id]
    my_activities = activities[activities["employee_id"] == employee_id]

    _, _, quarter = quarter_range(date.today())
    hero(
        f"{employee['name']}님의 성장 대시보드",
        f"{quarter} 학습 계획을 꾸준히 실행하고 있어요. 작은 기록이 큰 성장을 만듭니다.",
    )

    planned = my_goals["planned_hours"].sum()
    actual = my_activities["hours"].sum()
    completed = int((my_goals["status"] == "completed").sum())
    last_activity = (
        pd.to_datetime(my_activities["activity_date"]).max().date()
        if not my_activities.empty
        else None
    )
    streak_text = f"{(date.today() - last_activity).days}일 전 기록" if last_activity else "기록 없음"
    metric_row(planned, actual, completed, "최근 학습", streak_text)

    left, right = st.columns([1.65, 1], gap="large")
    with left:
        st.markdown('<div class="section-title">주별 계획과 수행</div>', unsafe_allow_html=True)
        weekly_chart(my_activities, planned)
        st.markdown('<div class="section-title">진행 중인 목표</div>', unsafe_allow_html=True)
        goal_cards(my_goals)

    with right:
        st.markdown('<div class="section-title">오늘의 체크포인트</div>', unsafe_allow_html=True)
        alerts = []
        for _, goal in my_goals[my_goals["status"] == "in_progress"].iterrows():
            _, progress = progress_for_goal(goal["goal_id"])
            expected = expected_progress(goal)
            if expected - progress >= 20:
                alerts.append(f"‘{goal['title']}’ 목표가 예상 진척도보다 {expected - progress:.0f}%p 늦어요.")
        if last_activity and (date.today() - last_activity).days >= 7:
            alerts.append("마지막 학습 기록 후 7일이 지났어요.")
        if alerts:
            for message in alerts:
                st.markdown(f'<div class="notice">⚡ {message}</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="success-note">✓ 현재 계획에 맞춰 순조롭게 진행 중입니다.</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="section-title">분야별 학습 시간</div>', unsafe_allow_html=True)
        if not my_activities.empty:
            category_data = my_activities.merge(
                my_goals[["goal_id", "category"]], on="goal_id", how="left"
            )
            category_summary = category_data.groupby("category")["hours"].sum().sort_values()
            st.bar_chart(category_summary, horizontal=True, color="#8175FF")

        st.markdown('<div class="section-title">최근 활동</div>', unsafe_allow_html=True)
        recent = my_activities.sort_values("activity_date", ascending=False).head(5)
        if recent.empty:
            st.caption("아직 학습 기록이 없습니다.")
        else:
            title_map = my_goals.set_index("goal_id")["title"].to_dict()
            for _, activity in recent.iterrows():
                st.markdown(
                    f"**{activity['activity_type']} · {activity['hours']:.1f}시간**  \n"
                    f"<span class='small-muted'>{activity['activity_date']} · "
                    f"{title_map.get(activity['goal_id'], '-')}</span>",
                    unsafe_allow_html=True,
                )
                st.divider()


def support_status(employee_id: str, goals: pd.DataFrame, activities: pd.DataFrame) -> str:
    person_goals = goals[goals["employee_id"] == employee_id]
    person_activities = activities[activities["employee_id"] == employee_id]
    if person_goals.empty:
        return "계획 필요"
    if person_activities.empty:
        return "기록 필요"
    latest = pd.to_datetime(person_activities["activity_date"]).max().date()
    if (date.today() - latest).days >= 14:
        return "장기 미기록"
    planned = person_goals["planned_hours"].sum()
    actual = person_activities["hours"].sum()
    rate = actual / planned * 100 if planned else 0
    expected = max(expected_progress(goal) for _, goal in person_goals.iterrows())
    if expected - rate >= 20:
        return "진척 지연"
    return "순조로움"


def team_dashboard(manager_id: str) -> None:
    employees = st.session_state.employees
    goals = st.session_state.goals
    activities = st.session_state.activities
    manager = employees.loc[employees["employee_id"] == manager_id].iloc[0]
    team_members = employees[employees["team"] == manager["team"]]
    ids = team_members["employee_id"].tolist()
    team_goals = goals[goals["employee_id"].isin(ids)]
    team_activities = activities[activities["employee_id"].isin(ids)]

    hero(
        f"{manager['team']} 학습 현황",
        "구성원의 순위를 매기기보다, 계획이 멈춘 지점을 발견하고 필요한 지원을 연결합니다.",
    )

    planned = team_goals["planned_hours"].sum()
    actual = team_activities["hours"].sum()
    completed = int((team_goals["status"] == "completed").sum())
    participants = team_activities["employee_id"].nunique()
    participation = participants / len(team_members) * 100 if len(team_members) else 0
    metric_row(planned, actual, completed, "학습 참여율", f"{participation:.0f}%")

    summary_rows = []
    for _, member in team_members.iterrows():
        member_goals = team_goals[team_goals["employee_id"] == member["employee_id"]]
        member_activities = team_activities[
            team_activities["employee_id"] == member["employee_id"]
        ]
        member_planned = member_goals["planned_hours"].sum()
        member_actual = member_activities["hours"].sum()
        latest = (
            pd.to_datetime(member_activities["activity_date"]).max().date()
            if not member_activities.empty
            else None
        )
        summary_rows.append(
            {
                "이름": member["name"],
                "직무": member["job"],
                "목표 수": len(member_goals),
                "계획 시간": round(member_planned, 1),
                "수행 시간": round(member_actual, 1),
                "달성률": round(min(member_actual / member_planned * 100, 100), 0)
                if member_planned
                else 0,
                "최근 기록일": latest.isoformat() if latest else "-",
                "상태": support_status(member["employee_id"], goals, activities),
            }
        )
    summary = pd.DataFrame(summary_rows)

    left, right = st.columns([1.5, 1], gap="large")
    with left:
        st.markdown('<div class="section-title">팀 학습 추이</div>', unsafe_allow_html=True)
        weekly_chart(team_activities, planned)
    with right:
        st.markdown('<div class="section-title">상태 분포</div>', unsafe_allow_html=True)
        status_counts = summary["상태"].value_counts()
        st.bar_chart(status_counts, horizontal=True, color="#5667FF")

    st.markdown('<div class="section-title">지원 필요 구성원</div>', unsafe_allow_html=True)
    needs_support = summary[summary["상태"] != "순조로움"]
    if needs_support.empty:
        st.markdown(
            '<div class="success-note">✓ 현재 특별한 지원 신호가 없습니다.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.dataframe(
            needs_support,
            width="stretch",
            hide_index=True,
            column_config={
                "달성률": st.column_config.ProgressColumn("달성률", min_value=0, max_value=100),
            },
        )

    st.markdown('<div class="section-title">구성원별 현황</div>', unsafe_allow_html=True)
    st.dataframe(
        summary,
        width="stretch",
        hide_index=True,
        column_config={
            "달성률": st.column_config.ProgressColumn("달성률", min_value=0, max_value=100),
        },
    )
    st.download_button(
        "팀 현황 CSV 다운로드",
        summary.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{manager['team']}_학습현황.csv",
        mime="text/csv",
    )


def organization_dashboard() -> None:
    employees = st.session_state.employees
    goals = st.session_state.goals
    activities = st.session_state.activities

    hero(
        "전사 학습 인사이트",
        "조직의 학습 흐름을 살펴보고 제도와 지원이 필요한 영역을 발견하세요.",
    )

    filter_cols = st.columns(3)
    divisions = ["전체"] + sorted(employees["division"].unique().tolist())
    selected_division = filter_cols[0].selectbox("본부", divisions)
    categories = ["전체"] + sorted(goals["category"].unique().tolist())
    selected_category = filter_cols[1].selectbox("학습 분야", categories)
    selected_status = filter_cols[2].selectbox(
        "목표 상태", ["전체"] + list(STATUS_LABEL.values())
    )

    filtered_employees = employees.copy()
    if selected_division != "전체":
        filtered_employees = filtered_employees[
            filtered_employees["division"] == selected_division
        ]
    ids = filtered_employees["employee_id"].tolist()
    filtered_goals = goals[goals["employee_id"].isin(ids)]
    if selected_category != "전체":
        filtered_goals = filtered_goals[filtered_goals["category"] == selected_category]
    if selected_status != "전체":
        status_key = next(key for key, value in STATUS_LABEL.items() if value == selected_status)
        filtered_goals = filtered_goals[filtered_goals["status"] == status_key]
    goal_ids = filtered_goals["goal_id"].tolist()
    filtered_activities = activities[activities["goal_id"].isin(goal_ids)]

    planned = filtered_goals["planned_hours"].sum()
    actual = filtered_activities["hours"].sum()
    completed = int((filtered_goals["status"] == "completed").sum())
    participants = filtered_activities["employee_id"].nunique()
    participation = participants / len(filtered_employees) * 100 if len(filtered_employees) else 0
    metric_row(planned, actual, completed, "학습 참여율", f"{participation:.0f}%")

    team_rows = []
    for team, members in filtered_employees.groupby("team"):
        member_ids = members["employee_id"].tolist()
        team_goals = filtered_goals[filtered_goals["employee_id"].isin(member_ids)]
        team_acts = filtered_activities[filtered_activities["employee_id"].isin(member_ids)]
        team_planned = team_goals["planned_hours"].sum()
        team_actual = team_acts["hours"].sum()
        headcount = len(members)
        team_rows.append(
            {
                "조직": team,
                "인원": headcount,
                "계획 등록률": round(team_goals["employee_id"].nunique() / headcount * 100)
                if headcount
                else 0,
                "학습 참여율": round(team_acts["employee_id"].nunique() / headcount * 100)
                if headcount
                else 0,
                "계획 시간": round(team_planned, 1),
                "수행 시간": round(team_actual, 1),
                "시간 달성률": round(min(team_actual / team_planned * 100, 100))
                if team_planned
                else 0,
            }
        )
    team_summary = pd.DataFrame(team_rows)

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        st.markdown('<div class="section-title">월별 학습 추이</div>', unsafe_allow_html=True)
        if filtered_activities.empty:
            st.info("선택한 조건에 해당하는 수행 내역이 없습니다.")
        else:
            monthly = filtered_activities.copy()
            monthly["월"] = pd.to_datetime(monthly["activity_date"]).dt.strftime("%Y-%m")
            monthly = monthly.groupby("월")["hours"].sum()
            st.line_chart(monthly, color="#5667FF")
    with right:
        st.markdown('<div class="section-title">학습 분야 분포</div>', unsafe_allow_html=True)
        if not filtered_activities.empty:
            category = filtered_activities.merge(
                filtered_goals[["goal_id", "category"]], on="goal_id", how="left"
            )
            category = category.groupby("category")["hours"].sum().sort_values()
            st.bar_chart(category, horizontal=True, color="#8175FF")

    st.markdown('<div class="section-title">조직별 현황</div>', unsafe_allow_html=True)
    if not team_summary.empty:
        display = team_summary.copy()
        for index, row in display.iterrows():
            if row["인원"] < 5:
                display.loc[index, ["계획 등록률", "학습 참여율", "계획 시간", "수행 시간", "시간 달성률"]] = pd.NA
        st.caption("개인정보 보호를 위해 5명 미만 조직의 집계 수치는 표시하지 않습니다.")
        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            column_config={
                "계획 등록률": st.column_config.NumberColumn(format="%d%%"),
                "학습 참여율": st.column_config.NumberColumn(format="%d%%"),
                "시간 달성률": st.column_config.ProgressColumn(
                    "시간 달성률", min_value=0, max_value=100
                ),
            },
        )
        st.download_button(
            "조직 현황 CSV 다운로드",
            team_summary.to_csv(index=False).encode("utf-8-sig"),
            file_name="전사_학습현황.csv",
            mime="text/csv",
        )


def goal_form(employee_id: str) -> None:
    _, q_end, quarter = quarter_range(date.today())
    hero("새 학습 목표 만들기", f"{quarter}에 집중할 성장 목표를 구체적으로 정해보세요.")

    with st.form("goal_form", clear_on_submit=True):
        title = st.text_input("목표명 *", placeholder="예: 데이터 분석 역량 강화")
        purpose = st.text_area(
            "학습 목적", placeholder="이 목표가 현재 업무와 성장에 어떤 도움이 되나요?"
        )
        c1, c2 = st.columns(2)
        category = c1.selectbox("학습 분야 *", list(CATEGORY_COLORS.keys()))
        planned_hours = c2.number_input(
            "목표 학습 시간 *", min_value=1.0, max_value=500.0, value=24.0, step=1.0
        )
        c3, c4 = st.columns(2)
        start_date = c3.date_input("시작일 *", value=date.today())
        end_date = c4.date_input("종료일 *", value=q_end)
        submitted = st.form_submit_button("목표 등록", type="primary", width="stretch")

    if submitted:
        if not title.strip():
            st.error("목표명을 입력해주세요.")
        elif start_date > end_date:
            st.error("종료일은 시작일보다 빠를 수 없습니다.")
        else:
            add_goal(
                {
                    "goal_id": f"G-{uuid4().hex[:8]}",
                    "employee_id": employee_id,
                    "title": title.strip(),
                    "category": category,
                    "purpose": purpose.strip(),
                    "start_date": start_date,
                    "end_date": end_date,
                    "planned_hours": float(planned_hours),
                    "status": "in_progress",
                    "created_at": datetime.now(),
                }
            )
            refresh_data()
            st.success("학습 목표를 등록했습니다. 개인 대시보드에서 확인할 수 있어요.")


def activity_form(employee_id: str) -> None:
    goals = st.session_state.goals
    my_goals = goals[
        (goals["employee_id"] == employee_id) & (goals["status"] == "in_progress")
    ]
    hero("학습 수행 기록", "오늘의 학습을 1분 안에 기록하고 계획 대비 진척도를 확인하세요.")

    if my_goals.empty:
        st.warning("진행 중인 목표가 없습니다. 먼저 학습 목표를 등록해주세요.")
        return

    goal_options = dict(zip(my_goals["title"], my_goals["goal_id"]))
    with st.form("activity_form", clear_on_submit=True):
        goal_title = st.selectbox("연결할 목표 *", list(goal_options.keys()))
        c1, c2, c3 = st.columns(3)
        activity_date = c1.date_input("학습일 *", value=date.today())
        activity_type = c2.selectbox(
            "활동 유형 *", ["강의", "독서", "자격증", "세미나", "프로젝트", "스터디", "기타"]
        )
        hours = c3.number_input(
            "수행 시간 *", min_value=0.5, max_value=24.0, value=1.0, step=0.5
        )
        memo = st.text_area(
            "학습 메모", placeholder="배운 내용과 업무에 적용할 포인트를 간단히 적어보세요."
        )
        submitted = st.form_submit_button("학습 기록 저장", type="primary", width="stretch")

    if submitted:
        add_activity(
            {
                "activity_id": f"A-{uuid4().hex[:8]}",
                "goal_id": goal_options[goal_title],
                "employee_id": employee_id,
                "activity_date": activity_date,
                "activity_type": activity_type,
                "hours": float(hours),
                "memo": memo.strip(),
                "created_at": datetime.now(),
            }
        )
        refresh_data()
        _, progress = progress_for_goal(goal_options[goal_title])
        st.success(f"학습 기록을 저장했습니다. 현재 목표 달성률은 {progress:.0f}%입니다.")


def user_registration() -> None:
    hero("사용자 등록", "사내 시스템 연동 없이 이 앱에서 바로 사용자 프로필을 만들 수 있습니다.")

    with st.form("user_registration_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("이름 *", placeholder="홍길동")
        email = c2.text_input("이메일 *", placeholder="name@example.com")
        c3, c4 = st.columns(2)
        division = c3.text_input("소속/본부 *", placeholder="제품개발본부")
        team = c4.text_input("팀 *", placeholder="플랫폼팀")
        c5, c6 = st.columns(2)
        job = c5.text_input("직무 *", placeholder="백엔드 개발")
        level = c6.selectbox(
            "직급/역할 *", ["사원", "프로", "선임", "매니저", "리더", "기타"]
        )
        submitted = st.form_submit_button("사용자 등록", type="primary", width="stretch")

    if submitted:
        values = [name, email, division, team, job]
        if any(not value.strip() for value in values):
            st.error("별표가 표시된 항목을 모두 입력해주세요.")
            return
        normalized_email = email.strip().lower()
        if "@" not in normalized_email or "." not in normalized_email.split("@")[-1]:
            st.error("올바른 이메일 주소를 입력해주세요.")
            return
        if normalized_email in set(st.session_state.employees["email"].str.lower()):
            st.error("이미 등록된 이메일입니다.")
            return

        employee_id = f"U-{uuid4().hex[:8]}"
        add_employee(
            {
                "employee_id": employee_id,
                "name": name.strip(),
                "email": normalized_email,
                "division": division.strip(),
                "team": team.strip(),
                "job": job.strip(),
                "level": level,
                "created_at": datetime.now().isoformat(),
            }
        )
        refresh_data()
        st.session_state.current_employee_id = employee_id
        st.session_state.registration_success = True
        st.rerun()


def data_management() -> None:
    hero("데이터 관리", "Google 스프레드시트에 저장된 데이터를 확인하고 내려받습니다.")
    st.info(
        "사용자, 목표, 학습 수행 데이터는 연결된 Google 스프레드시트의 "
        "users, goals, activities 시트에 저장됩니다."
    )
    tabs = st.tabs(["사용자", "목표", "수행 내역"])
    with tabs[0]:
        st.dataframe(st.session_state.employees, width="stretch", hide_index=True)
        st.download_button(
            "사용자 데이터 다운로드",
            st.session_state.employees.to_csv(index=False).encode("utf-8-sig"),
            "사용자.csv",
            "text/csv",
        )
    with tabs[1]:
        st.dataframe(st.session_state.goals, width="stretch", hide_index=True)
        st.download_button(
            "목표 데이터 다운로드",
            st.session_state.goals.to_csv(index=False).encode("utf-8-sig"),
            "학습목표.csv",
            "text/csv",
        )
    with tabs[2]:
        st.dataframe(st.session_state.activities, width="stretch", hide_index=True)
        st.download_button(
            "수행 데이터 다운로드",
            st.session_state.activities.to_csv(index=False).encode("utf-8-sig"),
            "학습수행.csv",
            "text/csv",
        )

def sidebar() -> tuple[str, str]:
    employees = st.session_state.employees
    with st.sidebar:
        st.markdown("## 🌱 Growlog")
        st.caption("Learning & Growth Dashboard")
        st.divider()

        role = st.selectbox("보기 권한", ["임직원", "팀 리더", "HRD / 경영진"])
        if role == "임직원":
            pages = [
                "나의 대시보드",
                "사용자 등록",
                "목표 등록",
                "수행 기록",
                "데이터 관리",
            ]
        elif role == "팀 리더":
            pages = ["팀 대시보드", "사용자 등록", "데이터 관리"]
        else:
            pages = ["전사 대시보드", "사용자 등록", "데이터 관리"]
        page = st.radio("메뉴", pages)

        st.divider()
        employee_labels = {
            f"{row['name']} · {row['email']}": row["employee_id"]
            for _, row in employees.iterrows()
        }
        current_label = next(
            label
            for label, employee_id in employee_labels.items()
            if employee_id == st.session_state.current_employee_id
        )
        selected_label = st.selectbox(
            "현재 사용자",
            list(employee_labels.keys()),
            index=list(employee_labels.keys()).index(current_label),
            help="등록된 사용자 중 현재 학습 기록을 입력할 계정을 선택합니다.",
        )
        st.session_state.current_employee_id = employee_labels[selected_label]
        selected = employees.loc[
            employees["employee_id"] == st.session_state.current_employee_id
        ].iloc[0]
        st.caption(f"{selected['team']} · {selected['job']}")

        st.divider()
        st.caption("Standalone MVP · Google Sheets storage")
    return role, page


def storage_setup_page(error: Exception) -> None:
    hero(
        "Google Sheets 연결 설정이 필요합니다",
        "서비스 계정과 스프레드시트 연결을 완료하면 사용자 등록 화면이 열립니다.",
    )
    st.error(str(error))
    st.markdown(
        """
        1. Google Cloud에서 Sheets API와 Drive API를 활성화합니다.
        2. 서비스 계정을 만들고 JSON 키를 발급합니다.
        3. 빈 Google 스프레드시트를 만들고 서비스 계정 이메일에 편집 권한으로 공유합니다.
        4. `.streamlit/secrets.toml.example`을 참고해 Streamlit Secrets를 입력합니다.

        자세한 절차는 `GOOGLE_SHEETS_DEPLOYMENT.md` 문서를 확인하세요.
        """
    )


def first_user_page() -> None:
    with st.sidebar:
        st.markdown("## 🌱 Growlog")
        st.caption("Learning & Growth Dashboard")
        st.divider()
        st.info("첫 사용자를 등록하면 대시보드가 시작됩니다.")
        st.caption("Google Sheets storage")
    user_registration()


def main() -> None:
    inject_css()
    try:
        initialize_state()
    except StorageConfigurationError as error:
        storage_setup_page(error)
        return

    if st.session_state.employees.empty:
        first_user_page()
        return

    role, page = sidebar()
    employee_id = st.session_state.current_employee_id
    if st.session_state.pop("registration_success", False):
        st.toast("사용자 등록이 완료되었습니다.", icon="✅")

    if page == "나의 대시보드":
        individual_dashboard(employee_id)
    elif page == "사용자 등록":
        user_registration()
    elif page == "목표 등록":
        goal_form(employee_id)
    elif page == "수행 기록":
        activity_form(employee_id)
    elif page == "팀 대시보드":
        team_dashboard(employee_id)
    elif page == "전사 대시보드":
        organization_dashboard()
    elif page == "데이터 관리":
        data_management()


if __name__ == "__main__":
    main()
