# 🍽 Lunch Radar

> 여의도 오피스 직장인을 위한 팀 점심 추천 앱

네이버 평점 · 혼잡도 · 팀 방문 이력을 종합해 오늘의 점심을 추천해주는 내부 도구입니다.  
Streamlit으로 구동되며, 별도 서버 없이 로컬에서 바로 실행할 수 있습니다.

---

## 주요 기능

| 탭 | 기능 |
|----|------|
| **추천** | 필터 기반 후보 선정 → 가중 랜덤 뽑기로 오늘의 점심 결정 |
| **식당 목록** | 전체 식당 검색 · 카테고리 필터 · 네이버 평점/리뷰 수 확인 |
| **방문 기록** | 팀원별 방문 날짜 · 개인 평점 · 메모 기록 |
| **관리** | 식당 추가/수정 · 네이버 데이터 수집 |

**추천 필터**
- 거리 상한 (1 / 3 / 5km)
- 카테고리 (한식 · 일식 · 중식 · 양식 · 베트남 · 태국 · 분식 · 카페 · 기타)
- 최근 7일 방문 식당 제외
- 혼잡한 곳 제외
- 카페 제외 (기본 ON)
- **전날 방문 카테고리 자동 제외** (기본 ON — 어제 한식 먹었으면 오늘 한식 목록에서 빠짐)

---

## 추천 점수 계산

상위 8개 후보를 선정한 뒤 점수를 가중치로 한 랜덤 뽑기를 진행합니다.

```
점수 = 거리 + 네이버평점 + 팀평점 + 혼잡도 + 최근방문 + 누적방문
```

| 요소 | 세부 기준 |
|------|-----------|
| 거리 | ≤1km +3.0 / ≤3km +2.0 / ≤5km +1.0 / 초과 −2.0 |
| 네이버 평점 | 별점 × 0.9 |
| 팀 평점 | 팀원 평균 × 0.8 |
| 혼잡도 | 여유 +2.0 / 보통 +0.5 / 혼잡 −2.0 |
| 최근 방문 | ≤3일 −4.0 / ≤7일 −2.0 / ≤14일 −0.5 / 14일+ +1.0 |
| 누적 방문 | ≥8회 −2.5 / ≥5회 −1.5 / ≥3회 −0.5 / 미만 +0.5 |

---

## 네이버 데이터 수집

Playwright(headless Chromium)로 `pcmap.place.naver.com`을 방문해  
GraphQL API 요청을 가로채고, 세션 쿠키를 재사용해 평점·리뷰 수를 수집합니다.

```
흐름: URL → place_id 추출 → pcmap 페이지 방문 →
      GraphQL 요청 인터셉트 → 쿠키 재사용해 API 직접 호출 → DB 저장
```

- 단일 식당 수집: 관리 탭 → 데이터 수집 → 선택 식당 수집
- 전체 일괄 수집: 관리 탭 → 데이터 수집 → 미수집 전체 수집
- 스크립트 실행: `python scripts/crawl_all_restaurants.py`

> 네이버 페이지 구조 변경 시 수집이 실패할 수 있습니다.  
> 혼잡도는 Naver Place GraphQL API에서 제공하지 않아 수집되지 않습니다.

---

## 설치 및 실행

**요구사항**: Python 3.11+

```bash
# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치 (네이버 크롤링용)
playwright install chromium

# 앱 실행
streamlit run app.py
```

앱 최초 실행 시 여의도 식당 136개가 자동으로 DB에 시드됩니다.

---

## 프로젝트 구조

```
Menu/
├── app.py                        # Streamlit 앱 (UI 전체)
├── requirements.txt
├── data/
│   └── lunch_menu.db             # SQLite DB (자동 생성)
├── lunch_app/
│   ├── db.py                     # DB 초기화 · 연결
│   ├── repository.py             # CRUD · 쿼리
│   ├── recommender.py            # 점수 계산 · 추천 정렬
│   ├── naver.py                  # 네이버 크롤러 (Playwright + GraphQL)
│   └── bootstrap.py              # 여의도 식당 초기 데이터
└── scripts/
    └── crawl_all_restaurants.py  # 일괄 수집 스크립트
```

---

## 기술 스택

| 역할 | 사용 기술 |
|------|-----------|
| UI | Streamlit |
| DB | SQLite (WAL 모드) |
| 크롤링 | Playwright · requests |
| 폰트 | Pretendard (Google Fonts) |

---

## 주의 사항

- 내부 팀 전용 MVP — 인증·권한 관리 미포함
- SQLite 파일(`data/lunch_menu.db`)은 로컬 전용. 클라우드 배포 시 PostgreSQL 전환 필요
- 네이버 크롤링은 비공식 방식이므로 과도한 호출은 삼가세요
