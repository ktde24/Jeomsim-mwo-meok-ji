from __future__ import annotations

import random
import time
from datetime import date

import streamlit as st

from lunch_app.bootstrap import normalize_restaurant_name, seed_yeouido_restaurants
from lunch_app.db import init_db
from lunch_app.naver import crawl_naver_place
from lunch_app.recommender import recommend
from lunch_app.repository import (
    add_crawl_log,
    add_restaurant,
    add_visit,
    get_restaurant,
    get_yesterday_categories,
    list_recent_logs,
    list_restaurants,
    list_visits,
    save_metrics,
    update_restaurant,
)


st.set_page_config(page_title="Lunch Radar", page_icon="🍽️", layout="wide")

CATEGORIES = ["전체", "한식", "일식", "중식", "양식", "베트남", "태국", "분식", "카페", "기타"]
DISTANCE_OPTIONS = [1, 3, 5]
PRICE_OPTIONS = ["", "~10000원", "10000~15000원", "15000~20000원", "20000원~"]
CONGESTION_LABEL = {1: "여유", 2: "보통", 3: "혼잡"}

# 카테고리별 색상 (배경, 텍스트, 액센트)
CAT_COLORS: dict[str, tuple[str, str, str]] = {
    "한식":   ("#FEF3C7", "#92400E", "#F59E0B"),
    "일식":   ("#EDE9FE", "#4C1D95", "#7C3AED"),
    "중식":   ("#FEE2E2", "#991B1B", "#EF4444"),
    "양식":   ("#DCFCE7", "#14532D", "#16A34A"),
    "베트남": ("#CCFBF1", "#134E4A", "#0D9488"),
    "태국":   ("#FEF9C3", "#713F12", "#CA8A04"),
    "분식":   ("#FFE4E6", "#881337", "#E11D48"),
    "카페":   ("#F3F4F6", "#1F2937", "#6B7280"),
    "기타":   ("#E0F2FE", "#0C4A6E", "#0284C7"),
}


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def ensure_bootstrap() -> None:
    init_db()
    seed_yeouido_restaurants()


# ── CSS ───────────────────────────────────────────────────────────────────────

def inject_styles() -> None:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, .stApp {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    background: #F5F4F0 !important;
    color: #111 !important;
}

.block-container { padding: 1.75rem 2.25rem 4rem !important; max-width: 1100px !important; }
section[data-testid="stSidebar"] { display: none; }

h1, h2, h3, h4 { font-weight: 800; letter-spacing: -0.025em; }

/* ── Tabs ── */
[data-testid="stTabs"] { gap: 0 !important; }
[data-testid="stTabs"] [role="tablist"] {
    gap: 0 !important;
    border-bottom: 1.5px solid #E2E0D9;
    margin-bottom: 1.75rem;
    background: transparent;
}
[data-testid="stTabs"] [role="tab"] {
    border: none !important; background: none !important;
    border-radius: 0 !important;
    padding: 0.65rem 1.2rem !important;
    font-size: 0.875rem; font-weight: 600;
    color: #9E9890 !important;
    border-bottom: 2.5px solid transparent !important;
    margin-bottom: -1.5px; transition: color 0.15s;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #111 !important;
    border-bottom-color: #111 !important;
}
[data-testid="stTabs"] [role="tab"]:hover { color: #444 !important; }

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #fff; border: 1px solid #E2E0D9;
    border-radius: 14px; padding: 1rem 1.1rem !important;
}
[data-testid="stMetricLabel"] p {
    color: #9E9890 !important; font-size: 0.72rem !important;
    font-weight: 700 !important; text-transform: uppercase; letter-spacing: 0.07em;
}
[data-testid="stMetricValue"] {
    font-size: 1.7rem !important; font-weight: 800 !important; color: #111 !important;
}

/* ── Form ── */
[data-testid="stForm"] {
    background: #fff; border: 1px solid #E2E0D9;
    border-radius: 18px; padding: 1.5rem 1.5rem 0.75rem !important;
}

/* ── Inputs ── */
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div {
    border-radius: 10px !important; border-color: #E2E0D9 !important;
    background: #FAFAF8 !important;
}
[data-baseweb="select"] > div { border-radius: 10px !important; border-color: #E2E0D9 !important; }
input, textarea { font-family: inherit !important; }

/* ── Buttons ── */
[data-testid="stButton"] > button {
    font-family: inherit !important; font-weight: 700 !important;
    border-radius: 10px !important; transition: all 0.15s !important;
    font-size: 0.875rem !important;
}
[data-testid="stButton"] > button[kind="primary"] {
    background: #111 !important; border: none !important; color: #fff !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.18) !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #2A2A2A !important; box-shadow: 0 3px 8px rgba(0,0,0,0.22) !important;
}
[data-testid="stButton"] > button[kind="secondary"] {
    background: #fff !important; border: 1px solid #D5D3CC !important; color: #111 !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover { background: #F5F4F0 !important; }

[data-testid="stAlert"] { border-radius: 12px !important; border: none !important; }
[data-testid="stProgress"] > div > div > div { background: #111 !important; border-radius: 99px !important; }
hr { border-color: #E2E0D9; margin: 1.25rem 0; }
[data-testid="stCaptionContainer"] p { color: #9E9890; font-size: 0.8rem; }

/* ── App header ── */
.app-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1.4rem 1.75rem;
    background: #111; color: #fff;
    border-radius: 20px; margin-bottom: 1.75rem;
    position: relative; overflow: hidden;
}
.app-header::before {
    content: '';
    position: absolute; top: -80px; right: -80px;
    width: 260px; height: 260px; border-radius: 50%;
    background: rgba(255,255,255,0.04);
    pointer-events: none;
}
.app-header::after {
    content: '';
    position: absolute; bottom: -50px; left: 30%;
    width: 180px; height: 180px; border-radius: 50%;
    background: rgba(255,255,255,0.03);
    pointer-events: none;
}
.app-header-title { font-size: 1.6rem; font-weight: 800; letter-spacing: -0.04em; color: #fff; line-height: 1; }
.app-header-sub   { font-size: 0.8rem; color: rgba(255,255,255,0.45); margin-top: 0.35rem; }
.app-header-stats { display: flex; gap: 0.5rem; }
.stat-chip {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px; padding: 0.55rem 1rem; text-align: center;
    backdrop-filter: blur(4px);
}
.stat-chip-num   { font-size: 1.3rem; font-weight: 800; color: #fff; line-height: 1; }
.stat-chip-label { font-size: 0.68rem; color: rgba(255,255,255,0.45); margin-top: 0.15rem;
                   font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }

/* ── Winner card ── */
.winner-card {
    background: linear-gradient(135deg, #1A1A2E 0%, #16213E 50%, #0F3460 100%);
    color: #fff; border-radius: 22px;
    padding: 1.75rem 2rem; margin-bottom: 1rem;
    position: relative; overflow: hidden;
    box-shadow: 0 8px 32px rgba(15,52,96,0.35);
}
.winner-card::before {
    content: ''; position: absolute; top: -100px; right: -80px;
    width: 300px; height: 300px; border-radius: 50%;
    background: radial-gradient(circle, rgba(96,165,250,0.12) 0%, transparent 70%);
}
.winner-card::after {
    content: ''; position: absolute; bottom: -60px; left: -40px;
    width: 200px; height: 200px; border-radius: 50%;
    background: radial-gradient(circle, rgba(167,139,250,0.1) 0%, transparent 70%);
}
.winner-inner { position: relative; z-index: 1; display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; }
.winner-eyebrow {
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.15em; color: rgba(255,255,255,0.4); margin-bottom: 0.55rem;
}
.winner-name {
    font-size: 2.1rem; font-weight: 800; letter-spacing: -0.04em;
    line-height: 1.05; margin-bottom: 0.45rem;
}
.winner-meta { font-size: 0.82rem; color: rgba(255,255,255,0.5); margin-bottom: 1rem; }
.winner-score-block { text-align: right; flex-shrink: 0; }
.winner-score-num   { font-size: 3rem; font-weight: 800; line-height: 1;
                      background: linear-gradient(135deg, #60A5FA, #A78BFA);
                      -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.winner-score-label { font-size: 0.68rem; color: rgba(255,255,255,0.35); margin-top: 0.1rem;
                      font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }

/* ── Cards ── */
.card {
    background: #fff; border: 1px solid #E2E0D9; border-radius: 16px;
    padding: 1.1rem 1.25rem 1rem; margin-bottom: 0.6rem;
    transition: box-shadow 0.2s, border-color 0.2s, transform 0.15s;
    border-left: 3.5px solid var(--accent, #E2E0D9);
}
.card:hover {
    box-shadow: 0 6px 24px rgba(0,0,0,0.08);
    border-color: var(--accent, #D5D3CC);
    transform: translateY(-1px);
}
.card-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; }
.card-name { font-size: 1rem; font-weight: 700; color: #111; line-height: 1.25; }
.card-sub  { font-size: 0.78rem; color: #9E9890; margin-top: 0.2rem; }
.card-rank { font-size: 0.75rem; font-weight: 800; color: var(--accent, #D5D3CC);
             background: color-mix(in srgb, var(--accent, #E2E0D9) 15%, transparent);
             padding: 0.1rem 0.45rem; border-radius: 6px; margin-right: 0.35rem; }
.cat-badge {
    display: inline-block; padding: 0.15rem 0.55rem; border-radius: 6px;
    font-size: 0.72rem; font-weight: 700;
    background: var(--cat-bg, #F3F4F6); color: var(--cat-text, #374151);
}
.rating-block { text-align: right; flex-shrink: 0; }
.rating-num   { font-size: 1.45rem; font-weight: 800; color: #111; line-height: 1; }
.rating-star  { font-size: 0.78rem; color: #F59E0B; }
.rating-label { font-size: 0.65rem; color: #C5C0B8; margin-top: 0.1rem; }

/* ── Pills ── */
.pills { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.6rem; }
.pill {
    display: inline-flex; align-items: center; gap: 0.2rem;
    padding: 0.22rem 0.6rem; border-radius: 99px;
    font-size: 0.76rem; font-weight: 600; white-space: nowrap;
    background: #F0EEE9; color: #6E6860;
}
.pill-green  { background: #DCFCE7; color: #15803D; }
.pill-amber  { background: #FEF3C7; color: #92400E; }
.pill-red    { background: #FEE2E2; color: #B91C1C; }
.pill-blue   { background: #DBEAFE; color: #1D4ED8; }
.pill-naver  { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; text-decoration: none; }
.pill-naver:hover { background: #D1FAE5; }

/* ── Misc ── */
.section-label {
    font-size: 0.68rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.12em; color: #C5C0B8; margin: 1.5rem 0 0.75rem;
    display: flex; align-items: center; gap: 0.5rem;
}
.section-label::after {
    content: ''; flex: 1; height: 1px; background: #E8E6DF;
}

.visit-item {
    display: flex; align-items: flex-start; gap: 0.75rem;
    padding: 0.9rem 0; border-bottom: 1px solid #F0EEE9;
}
.avatar {
    width: 34px; height: 34px; border-radius: 50%;
    background: #F0EEE9; display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 800; color: #7A7268; flex-shrink: 0;
}
.visit-name  { font-size: 0.9rem; font-weight: 700; color: #111; }
.visit-meta  { font-size: 0.77rem; color: #9E9890; margin-top: 0.1rem; }
.visit-memo  { font-size: 0.77rem; color: #6E6860; margin-top: 0.2rem; }

.log-item {
    display: flex; align-items: center; gap: 0.65rem;
    padding: 0.6rem 0; border-bottom: 1px solid #F0EEE9; font-size: 0.82rem;
}
.log-dot  { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-ok   { background: #22C55E; }
.dot-err  { background: #EF4444; }
.log-name { font-weight: 700; color: #111; flex: 1; }
.log-time { color: #9E9890; font-size: 0.75rem; }
.log-msg  { color: #6E6860; font-size: 0.75rem; }

.empty-state {
    text-align: center; padding: 3.5rem 1rem; color: #B0A898;
    font-size: 0.9rem; line-height: 1.7;
}

.filter-row {
    display: flex; align-items: center; gap: 0.5rem;
    background: #fff; border: 1px solid #E2E0D9;
    border-radius: 14px; padding: 0.7rem 1rem; margin-bottom: 1.25rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def dname(r: dict) -> str:
    return normalize_restaurant_name(r["name"])

def fmt(v, fallback="—") -> str:
    if v is None or v == "" or v == 0:
        return fallback
    return str(v)

def _cat_style(cat: str) -> str:
    bg, text, accent = CAT_COLORS.get(cat, ("#F3F4F6", "#374151", "#9CA3AF"))
    return f"--accent:{accent}; --cat-bg:{bg}; --cat-text:{text};"

def rating_pill(r: dict) -> str:
    v = r.get("rating")
    return f'<span class="pill pill-amber">★ {v}</span>' if v else ""

def review_pill(r: dict) -> str:
    v = r.get("review_count")
    return f'<span class="pill pill-blue">리뷰 {v:,}</span>' if v else ""

def congestion_pill(r: dict) -> str:
    score = r.get("congestion_score")
    if score is None:
        return ""
    label = CONGESTION_LABEL.get(score, "")
    if not label:
        return ""
    cls = {1: "pill-green", 2: "pill-amber", 3: "pill-red"}.get(score, "")
    return f'<span class="pill {cls}">{label}</span>'

def naver_pill(url: str | None) -> str:
    if not url:
        return ""
    return f'<a class="pill pill-naver" href="{url}" target="_blank">N 보기</a>'

def dist_pill(r: dict) -> str:
    d = float(r.get("distance_km") or 0)
    return f'<span class="pill">{d:.1f}km</span>'

def visit_badge(r: dict) -> str:
    vc = int(r.get("visit_count") or 0)
    if vc == 0:
        return '<span class="pill">미방문</span>'
    return f'<span class="pill pill-green">{vc}회 방문</span>'

def cat_badge(cat: str) -> str:
    bg, text, _ = CAT_COLORS.get(cat, ("#F3F4F6", "#374151", "#9CA3AF"))
    return f'<span class="cat-badge" style="background:{bg};color:{text};">{cat}</span>'

def filter_restaurants(
    restaurants, category, max_dist, excl_recent, excl_crowd,
    excl_cafe=False, excl_categories: set[str] | None = None,
):
    excl_categories = excl_categories or set()
    out = []
    for r in restaurants:
        if category != "전체" and r["category"] != category:
            continue
        if excl_cafe and r["category"] == "카페":
            continue
        if r["category"] in excl_categories:
            continue
        if float(r["distance_km"]) > max_dist:
            continue
        if excl_crowd and r.get("congestion_score") == 3:
            continue
        if excl_recent and r.get("last_visited_on"):
            days = (date.today() - date.fromisoformat(r["last_visited_on"])).days
            if days <= 7:
                continue
        out.append(r)
    return out


# ── Tab: 추천 ─────────────────────────────────────────────────────────────────

def tab_recommend(restaurants: list[dict]) -> None:
    col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns([1.4, 1.1, 1, 1, 1, 1.2])
    category      = col_f1.selectbox("카테고리", CATEGORIES, key="rec_category", label_visibility="collapsed")
    max_dist      = col_f2.selectbox("거리", DISTANCE_OPTIONS, index=1, key="rec_dist",
                                     format_func=lambda v: f"{v}km 이내", label_visibility="collapsed")
    excl_rec      = col_f3.checkbox("최근 방문 제외", value=True, key="rec_excl_recent")
    excl_crowd    = col_f4.checkbox("혼잡한 곳 제외", key="rec_excl_crowd")
    excl_cafe     = col_f5.checkbox("카페 제외", value=True, key="rec_excl_cafe")
    excl_yesterday = col_f6.checkbox("전날 카테고리 제외", value=True, key="rec_excl_yesterday")

    yesterday_cats: set[str] = get_yesterday_categories() if excl_yesterday else set()
    # 카테고리 직접 선택 시에는 전날 제외 무시
    active_excl_cats = yesterday_cats if category == "전체" else set()

    if active_excl_cats:
        cats_str = ", ".join(sorted(active_excl_cats))
        st.info(f"어제 방문한 카테고리 제외 중: **{cats_str}**")

    candidates = filter_restaurants(
        restaurants, category, max_dist, excl_rec, excl_crowd, excl_cafe,
        excl_categories=active_excl_cats,
    )
    ranked = recommend(candidates)

    if not ranked:
        st.markdown('<div class="empty-state">조건에 맞는 식당이 없어요.<br>필터를 완화해보세요.</div>', unsafe_allow_html=True)
        return

    pool = ranked[: min(8, len(ranked))]
    spin_slot = st.empty()

    if st.button("오늘의 점심 뽑기 🎲", type="primary", use_container_width=True, key="spin_btn"):
        names = [dname(r) for r in pool]
        for _ in range(18):
            pick = random.choice(names)
            spin_slot.markdown(
                f'<div class="winner-card">'
                f'<div class="winner-inner">'
                f'<div><div class="winner-eyebrow">뽑는 중…</div>'
                f'<div class="winner-name">{pick}</div></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            time.sleep(0.06)
        weights = [max(r["recommendation_score"], 0.1) for r in pool]
        st.session_state.roulette = random.choices(pool, weights=weights, k=1)[0]

    top = st.session_state.get("roulette") or ranked[0]
    reasons_html = "".join(f'<span class="pill">{x}</span>' for x in top.get("recommendation_reasons", []))
    score_display = f"{top['recommendation_score']:.1f}"
    spin_slot.markdown(f"""
<div class="winner-card">
    <div class="winner-inner">
        <div style="flex:1;min-width:0;">
            <div class="winner-eyebrow">Today's Pick</div>
            <div class="winner-name">{dname(top)}</div>
            <div class="winner-meta">{top['category']} · {top['distance_km']}km</div>
            <div class="pills">
                {rating_pill(top)}{review_pill(top)}{congestion_pill(top)}{naver_pill(top.get('naver_url'))}
                {reasons_html}
            </div>
        </div>
        <div class="winner-score-block">
            <div class="winner-score-num">{score_display}</div>
            <div class="winner-score-label">추천점수</div>
        </div>
    </div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-label">Shortlist</div>', unsafe_allow_html=True)
    for i, r in enumerate(ranked[:6]):
        style = _cat_style(r["category"])
        tags_html = "".join(f'<span class="pill">{t.strip()}</span>' for t in (r.get("tags") or "").split(",") if t.strip())
        rating_v = r.get("rating")
        rating_html = (
            f'<div class="rating-num">{rating_v}</div><div class="rating-star">★★★★★</div><div class="rating-label">별점</div>'
            if rating_v else '<div class="rating-num" style="color:#D5D3CC;">—</div><div class="rating-label">미수집</div>'
        )
        st.markdown(f"""
<div class="card" style="{style}">
    <div class="card-row">
        <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.3rem;">
                <span class="card-rank" style="--accent:{CAT_COLORS.get(r['category'], ('','','#aaa'))[2]};">#{i+1}</span>
                <span class="card-name">{dname(r)}</span>
            </div>
            <div class="card-sub">{cat_badge(r['category'])} &nbsp;{r['distance_km']}km</div>
        </div>
        <div class="rating-block">{rating_html}</div>
    </div>
    <div class="pills">
        {review_pill(r)}{congestion_pill(r)}{dist_pill(r)}{tags_html}{naver_pill(r.get('naver_url'))}
    </div>
</div>""", unsafe_allow_html=True)

    no_rating = sum(1 for r in restaurants if not r.get("rating") and r.get("naver_url"))
    if no_rating:
        st.caption(f"평점 미수집 {no_rating}개 · 관리 탭에서 데이터 수집 가능")


# ── Tab: 식당 목록 ────────────────────────────────────────────────────────────

def tab_directory(restaurants: list[dict]) -> None:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("전체", len(restaurants))
    m2.metric("평점 수집", sum(1 for r in restaurants if r.get("rating")))
    m3.metric("리뷰 수집", sum(1 for r in restaurants if r.get("review_count")))
    m4.metric("방문 있음", sum(1 for r in restaurants if int(r.get("visit_count") or 0) > 0))

    st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)

    sc1, sc2 = st.columns([2.5, 1])
    search = sc1.text_input("검색", placeholder="식당명, 태그, 주소 검색…", key="dir_search", label_visibility="collapsed")
    cat_f  = sc2.selectbox("카테고리", CATEGORIES, key="dir_category", label_visibility="collapsed")

    filtered = [
        r for r in restaurants
        if (not search.strip() or search.strip().lower() in " ".join([dname(r), r.get("tags") or "", r.get("address") or ""]).lower())
        and (cat_f == "전체" or r["category"] == cat_f)
    ]

    st.caption(f"{len(filtered)}개 표시")

    for i in range(0, len(filtered), 2):
        cols = st.columns(2, gap="small")
        for j, col in enumerate(cols):
            if i + j >= len(filtered):
                break
            r = filtered[i + j]
            style = _cat_style(r["category"])
            lv = f'마지막 {r["last_visited_on"]}' if r.get("last_visited_on") else ""
            tags_html = "".join(f'<span class="pill">{t.strip()}</span>' for t in (r.get("tags") or "").split(",") if t.strip())
            rating_v = r.get("rating")
            rating_html = (
                f'<div class="rating-num">{rating_v}</div><div class="rating-star">★</div>'
                if rating_v else '<div class="rating-num" style="color:#D5D3CC;font-size:1.1rem;">—</div>'
            )
            with col:
                st.markdown(f"""
<div class="card" style="{style}">
    <div class="card-row">
        <div style="flex:1;min-width:0;">
            <div class="card-name">{dname(r)}</div>
            <div class="card-sub" style="margin-top:0.25rem;">
                {cat_badge(r['category'])} &nbsp;{r['distance_km']}km
                {(' · ' + r['price_level']) if r.get('price_level') else ''}
            </div>
        </div>
        <div class="rating-block">{rating_html}<div class="rating-label">별점</div></div>
    </div>
    <div class="pills">
        {visit_badge(r)}{review_pill(r)}{tags_html}{naver_pill(r.get('naver_url'))}
    </div>
    {'<div class="card-sub" style="margin-top:0.45rem;font-size:0.73rem;">' + lv + '</div>' if lv else ''}
</div>""", unsafe_allow_html=True)


# ── Tab: 방문 기록 ────────────────────────────────────────────────────────────

def tab_visits(restaurants: list[dict]) -> None:
    col_form, col_hist = st.columns([1, 1.5], gap="large")

    with col_form:
        st.markdown("#### 방문 기록 남기기")
        option_map = {dname(r): r["id"] for r in restaurants}
        with st.form("visit_form", clear_on_submit=True):
            rest = st.selectbox("식당", list(option_map.keys()), key="vf_rest")
            name = st.text_input("이름", placeholder="예: 민지", key="vf_name")
            on   = st.date_input("방문일", value=date.today(), key="vf_date")
            rate = st.slider("개인 평점", 0.0, 5.0, 4.0, 0.5, key="vf_rate")
            memo = st.text_area("메모", placeholder="웨이팅 짧았음, 추천 메뉴 등", height=90, key="vf_memo")
            if st.form_submit_button("저장", use_container_width=True, type="primary"):
                if not name.strip():
                    st.error("이름을 입력해주세요.")
                else:
                    add_visit({"restaurant_id": option_map[rest], "user_name": name.strip(),
                               "visited_on": on.isoformat(), "user_rating": rate, "memo": memo.strip()})
                    st.success("기록했어요!")
                    st.rerun()

    with col_hist:
        st.markdown("#### 최근 방문")
        visits = list_visits(limit=40)
        if not visits:
            st.markdown('<div class="empty-state">방문 기록이 없어요.</div>', unsafe_allow_html=True)
        else:
            for v in visits:
                init   = (v["user_name"][0] if v["user_name"] else "?").upper()
                stars  = "★" * int(v.get("user_rating") or 0)
                memo_h = f'<div class="visit-memo">{v["memo"]}</div>' if v.get("memo") else ""
                st.markdown(f"""
<div class="visit-item">
    <div class="avatar">{init}</div>
    <div>
        <div class="visit-name">{normalize_restaurant_name(v['restaurant_name'])}</div>
        <div class="visit-meta">{v['visited_on']} · {v['user_name']} · <span style="color:#F59E0B;">{stars}</span></div>
        {memo_h}
    </div>
</div>""", unsafe_allow_html=True)


# ── Tab: 관리 ─────────────────────────────────────────────────────────────────

def tab_manage(restaurants: list[dict]) -> None:
    sub = st.radio("", ["식당 추가", "식당 수정", "데이터 수집"],
                   horizontal=True, key="manage_sub", label_visibility="collapsed")
    st.markdown('<div style="height:0.25rem;"></div>', unsafe_allow_html=True)

    if sub == "식당 추가":
        _panel_add()
    elif sub == "식당 수정":
        _panel_edit(restaurants)
    else:
        _panel_crawl(restaurants)


def _panel_add() -> None:
    st.markdown("#### 새 식당 등록")
    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name     = c1.text_input("식당명 *", key="af_name")
        category = c2.selectbox("카테고리", CATEGORIES[1:], key="af_cat")
        c3, c4   = st.columns(2)
        dist     = c3.number_input("거리(km)", 0.1, 10.0, 1.0, 0.1, key="af_dist")
        price    = c4.selectbox("가격대", PRICE_OPTIONS, key="af_price")
        address  = st.text_input("주소", key="af_addr")
        url      = st.text_input("네이버 URL", placeholder="map.naver.com/… 또는 naver.me/…", key="af_url")
        tags     = st.text_input("태그", placeholder="국밥, 웨이팅 짧음, 혼밥", key="af_tags")
        note     = st.text_area("메모", height=80, key="af_note")
        if st.form_submit_button("등록", use_container_width=True, type="primary"):
            if not name.strip():
                st.error("식당명을 입력하세요.")
            else:
                add_restaurant({"name": name.strip(), "category": category, "distance_km": dist,
                                "address": address.strip(), "naver_url": url.strip(),
                                "price_level": price, "tags": tags.strip(), "note": note.strip()})
                st.success(f"'{name.strip()}' 등록했어요!")
                st.rerun()


def _panel_edit(restaurants: list[dict]) -> None:
    st.markdown("#### 식당 정보 수정")
    if not restaurants:
        st.markdown('<div class="empty-state">등록된 식당이 없어요.</div>', unsafe_allow_html=True)
        return
    opts = {f"{dname(r)}  ({r['category']})": r["id"] for r in restaurants}
    sel_label = st.selectbox("수정할 식당", list(opts.keys()), key="edit_select")
    sel = get_restaurant(opts[sel_label])
    if not sel:
        return
    with st.form("edit_form"):
        c1, c2 = st.columns(2)
        u_name  = c1.text_input("식당명", value=sel["name"], key="ef_name")
        u_cat   = c2.selectbox("카테고리", CATEGORIES[1:], key="ef_cat",
                               index=CATEGORIES[1:].index(sel["category"]) if sel["category"] in CATEGORIES[1:] else 0)
        c3, c4  = st.columns(2)
        u_dist  = c3.number_input("거리(km)", 0.1, 10.0, float(sel["distance_km"]), 0.1, key="ef_dist")
        u_price = c4.selectbox("가격대", PRICE_OPTIONS, key="ef_price",
                               index=PRICE_OPTIONS.index(sel.get("price_level") or "") if (sel.get("price_level") or "") in PRICE_OPTIONS else 0)
        u_addr  = st.text_input("주소", value=sel.get("address") or "", key="ef_addr")
        u_url   = st.text_input("네이버 URL", value=sel.get("naver_url") or "", key="ef_url")
        u_tags  = st.text_input("태그", value=sel.get("tags") or "", key="ef_tags")
        u_note  = st.text_area("메모", value=sel.get("note") or "", height=80, key="ef_note")
        if st.form_submit_button("저장", use_container_width=True, type="primary"):
            update_restaurant(sel["id"], {"name": u_name.strip(), "category": u_cat,
                                          "distance_km": u_dist, "address": u_addr.strip(),
                                          "naver_url": u_url.strip(), "price_level": u_price,
                                          "tags": u_tags.strip(), "note": u_note.strip()})
            st.success("저장했어요.")
            st.rerun()


def _panel_crawl(restaurants: list[dict]) -> None:
    st.markdown("#### 네이버 데이터 수집")

    with_url  = [r for r in restaurants if r.get("naver_url")]
    no_rating = [r for r in with_url if not r.get("rating")]
    no_review = [r for r in with_url if not r.get("review_count")]

    m1, m2, m3 = st.columns(3)
    m1.metric("수집 가능", len(with_url))
    m2.metric("평점 미수집", len(no_rating))
    m3.metric("리뷰 미수집", len(no_review))

    st.markdown("---")

    if not with_url:
        st.markdown('<div class="empty-state">네이버 URL이 등록된 식당이 없어요.</div>', unsafe_allow_html=True)
        return

    opts = {f"{dname(r)}  ·  {r['category']}": r for r in with_url}
    sel_name = st.selectbox("수집할 식당", list(opts.keys()), key="crawl_select")
    sel_r = opts[sel_name]

    c1, c2 = st.columns(2)
    if c1.button("선택 식당 수집", use_container_width=True, type="primary", key="crawl_single"):
        with st.spinner("수집 중…"):
            try:
                m = crawl_naver_place(sel_r["naver_url"])
                save_metrics(sel_r["id"], m)
                add_crawl_log(sel_r["id"], "success", "수집 성공")
                st.success(f"완료  ·  별점 {m.get('rating') or '없음'}  ·  리뷰 {m.get('review_count') or 0:,}개")
                st.rerun()
            except Exception as e:
                add_crawl_log(sel_r["id"], "error", str(e))
                st.error(f"실패: {e}")

    targets   = no_rating if no_rating else with_url
    btn_label = f"미수집 {len(targets)}개 전체 수집" if no_rating else f"전체 {len(targets)}개 재수집"
    if c2.button(btn_label, use_container_width=True, key="crawl_all"):
        prog = st.progress(0, text="준비 중…")
        ok, err = 0, 0
        for idx, r in enumerate(targets):
            prog.progress((idx + 1) / len(targets), text=f"{dname(r)} ({idx+1}/{len(targets)})")
            try:
                m = crawl_naver_place(r["naver_url"])
                save_metrics(r["id"], m)
                add_crawl_log(r["id"], "success", "수집 성공")
                ok += 1
            except Exception as e:
                add_crawl_log(r["id"], "error", str(e))
                err += 1
            time.sleep(0.15)
        prog.empty()
        st.info(f"완료  ·  성공 {ok}건 / 실패 {err}건")
        st.rerun()

    st.markdown('<div class="section-label">최근 수집 로그</div>', unsafe_allow_html=True)
    logs = list_recent_logs(limit=25)
    if not logs:
        st.caption("로그 없음")
    for log in logs:
        dot = "dot-ok" if log["status"] == "success" else "dot-err"
        st.markdown(f"""
<div class="log-item">
    <div class="log-dot {dot}"></div>
    <div class="log-name">{normalize_restaurant_name(log['restaurant_name'])}</div>
    <div class="log-time">{log['crawled_at']}</div>
    <div class="log-msg">{log['message']}</div>
</div>""", unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ensure_bootstrap()
    inject_styles()

    restaurants = list_restaurants()
    total    = len(restaurants)
    rated    = sum(1 for r in restaurants if r.get("rating"))
    reviewed = sum(1 for r in restaurants if r.get("review_count"))

    st.markdown(f"""
<div class="app-header">
    <div>
        <div class="app-header-title">🍽 Lunch Radar</div>
        <div class="app-header-sub">여의도 점심 추천 · 미래에셋증권빌딩 기준</div>
    </div>
    <div class="app-header-stats">
        <div class="stat-chip">
            <div class="stat-chip-num">{total}</div>
            <div class="stat-chip-label">식당</div>
        </div>
        <div class="stat-chip">
            <div class="stat-chip-num">{rated}</div>
            <div class="stat-chip-label">평점</div>
        </div>
        <div class="stat-chip">
            <div class="stat-chip-num">{reviewed}</div>
            <div class="stat-chip-label">리뷰</div>
        </div>
    </div>
</div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["  추천  ", "  식당 목록  ", "  방문 기록  ", "  관리  "])
    with tab1: tab_recommend(restaurants)
    with tab2: tab_directory(restaurants)
    with tab3: tab_visits(restaurants)
    with tab4: tab_manage(restaurants)


if __name__ == "__main__":
    main()
