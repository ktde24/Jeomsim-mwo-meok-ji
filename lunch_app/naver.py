from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import parse_qs, quote, unquote, urlparse

import requests

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover
    sync_playwright = None


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    )
}

GRAPHQL_URL = "https://pcmap-api.place.naver.com/graphql"

_VISITOR_REVIEW_STATS_QUERY = """
query getVisitorReviewStats($id: String) {
  visitorReviewStats(id: $id) {
    id
    review {
      avgRating
      totalCount
    }
  }
}
""".strip()


# ---------------------------------------------------------------------------
# URL 파싱
# ---------------------------------------------------------------------------

def _extract_place_id(url: str) -> str | None:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    for key in ("id", "placeId"):
        values = query.get(key)
        if values and values[0].isdigit():
            return values[0]

    patterns = [
        r"/entry/place/(\d+)",
        r"/restaurant/(\d+)",
        r"/place/(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _is_search_url(url: str) -> bool:
    return (
        "map.naver.com/p/search/" in url
        or "search.naver.com/search.naver" in url
        or "m.search.naver.com/search.naver" in url
    )


def _extract_search_query(url: str) -> str | None:
    parsed = urlparse(url)
    if "map.naver.com" in parsed.netloc and "/p/search/" in parsed.path:
        query = parsed.path.split("/p/search/", 1)[1]
        return unquote(query).strip("/") if query else None
    params = parse_qs(parsed.query)
    for key in ("query", "where"):
        values = params.get(key)
        if values:
            return values[0]
    return None


def _search_query_variants(query: str) -> list[str]:
    """긴 검색어(식당명+주소)에서 짧은 후보 쿼리들을 생성."""
    variants = [query]
    city_markers = ["서울", "경기", "부산", "인천", "대구", "대전", "광주", "울산", "세종", "강원", "충청", "전라", "경상", "제주"]
    tokens = query.split()
    for i, token in enumerate(tokens):
        if i > 0 and any(token.startswith(m) for m in city_markers):
            short = " ".join(tokens[:i])
            if short and short not in variants:
                variants.append(short)
            break
    if len(tokens) > 3:
        short3 = " ".join(tokens[:3])
        if short3 not in variants:
            variants.append(short3)
    return variants


def _resolve_place_id_via_requests(url: str) -> str | None:
    """검색 URL에서 requests로 place_id 추출 시도."""
    query = _extract_search_query(url)
    if not query:
        return None

    patterns = [
        r"https://m\.place\.naver\.com/restaurant/(\d+)",
        r"https://m\.place\.naver\.com/place/(\d+)",
        r"https://pcmap\.place\.naver\.com/restaurant/(\d+)",
        r"https://pcmap\.place\.naver\.com/place/(\d+)",
    ]

    for q in _search_query_variants(query):
        search_url = f"https://m.search.naver.com/search.naver?query={quote(q)}"
        try:
            resp = requests.get(search_url, headers=HEADERS, timeout=12)
            resp.raise_for_status()
        except Exception:
            continue
        for pattern in patterns:
            match = re.search(pattern, resp.text)
            if match:
                return match.group(1)
    return None


def _can_use_playwright() -> bool:
    return sync_playwright is not None


# ---------------------------------------------------------------------------
# GraphQL 방식 (Playwright로 쿠키 획득 후 직접 호출)
# ---------------------------------------------------------------------------

def _fetch_via_graphql(place_id: str) -> dict | None:
    """
    pcmap 페이지를 방문해 세션 쿠키를 얻고, GraphQL API로 평점/리뷰 수를 가져온다.
    """
    if not _can_use_playwright():
        return None

    pcmap_url = f"https://pcmap.place.naver.com/restaurant/{place_id}/home"
    captured_requests: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(extra_http_headers=HEADERS)

        def on_request(req):
            if GRAPHQL_URL in req.url:
                body = req.post_data
                if body:
                    try:
                        parsed = json.loads(body)
                        ops = parsed if isinstance(parsed, list) else [parsed]
                        op_names = [op.get("operationName") for op in ops if isinstance(op, dict)]
                        if "getVisitorReviewStats" in op_names or "getVisitorReviews" in op_names:
                            captured_requests.append({"headers": dict(req.headers), "body": body})
                    except Exception:
                        pass

        page.on("request", on_request)
        page.goto(pcmap_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        cookies = page.context.cookies()
        browser.close()

    if not captured_requests:
        return None

    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

    rating = None
    review_count = None

    for req_data in captured_requests:
        headers = dict(req_data["headers"])
        headers["cookie"] = cookie_str
        try:
            resp = requests.post(GRAPHQL_URL, data=req_data["body"], headers=headers, timeout=10)
            if resp.status_code != 200:
                continue
            data = resp.json()
            data_str = json.dumps(data)

            # JSON 파싱으로 visitorReviewStats.review 직접 접근
            try:
                parsed = resp.json()
                items = parsed if isinstance(parsed, list) else [parsed]
                for item in items:
                    stats = (item.get("data") or {}).get("visitorReviewStats")
                    if not stats:
                        continue
                    review = stats.get("review") or {}
                    if rating is None:
                        avg = review.get("avgRating")
                        if avg and float(avg) > 0:
                            rating = float(avg)
                    if review_count is None:
                        total = review.get("totalCount")
                        if total and int(total) > 0:
                            review_count = int(total)
            except Exception:
                pass

        except Exception:
            continue

    if rating is None and review_count is None:
        return None

    return {
        "rating": rating,
        "review_count": review_count,
        "congestion_text": None,
        "congestion_score": None,
        "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "naver-graphql",
        "raw_summary": json.dumps(
            {"place_id": place_id, "rating_found": rating is not None, "review_count_found": review_count is not None},
            ensure_ascii=True,
        ),
    }


# ---------------------------------------------------------------------------
# HTML 파싱 fallback (평점이 GraphQL에서 안 나올 경우)
# ---------------------------------------------------------------------------

def _parse_float(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
    return float(match.group(1)) if match else None


def _parse_int(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d+)", text.replace(",", ""))
    return int(match.group(1)) if match else None


def _congestion_to_score(text: str | None) -> int | None:
    if not text:
        return None
    normalized = text.strip()
    if "대기공간" in normalized or "대기 공간" in normalized:
        return None
    if any(token in normalized for token in ["여유", "원활", "한산"]):
        return 1
    if any(token in normalized for token in ["보통", "무난", "적당"]):
        return 2
    if any(token in normalized for token in ["혼잡", "붐빔", "대기", "복잡"]):
        return 3
    return None


def _fetch_via_html(place_id: str) -> dict | None:
    """pcmap HTML을 Playwright로 렌더링하여 평점/리뷰 수/혼잡도를 파싱."""
    if not _can_use_playwright():
        return None

    pcmap_url = f"https://pcmap.place.naver.com/restaurant/{place_id}/home"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(extra_http_headers=HEADERS)
        page.goto(pcmap_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    rating = None
    review_count = None
    congestion_text = None

    # 평점: <span class="place_blind">별점</span>4.44 패턴
    m = re.search(r'place_blind[^>]*>별점</span>\s*([\d.]+)', html)
    if m:
        v = float(m.group(1))
        if 0 < v <= 5:
            rating = v

    # 리뷰 수: visitorReviewsTotal (방문자 리뷰 총 수)
    m = re.search(r'visitorReviewsTotal[\" ]*:\s*(\d+)', html)
    if m and int(m.group(1)) > 0:
        review_count = int(m.group(1))

    # 혼잡도 (텍스트 기반) — 한글 문자만 캡처해 JSON 오염 방지
    body_text_match = re.search(
        r'(현재\s*[가-힣]{2,6}|혼잡[가-힣]{0,4}|여유[가-힣]{0,4}|보통[가-힣]{0,4}|붐빔[가-힣]{0,4})',
        html,
    )
    if body_text_match:
        candidate = body_text_match.group(1).strip()
        if "대기공간" not in candidate and len(candidate) <= 10:
            congestion_text = candidate

    if rating is None and review_count is None:
        return None

    return {
        "rating": rating,
        "review_count": review_count,
        "congestion_text": congestion_text,
        "congestion_score": _congestion_to_score(congestion_text),
        "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "naver-html",
        "raw_summary": json.dumps(
            {"place_id": place_id, "rating_found": rating is not None, "review_count_found": review_count is not None},
            ensure_ascii=True,
        ),
    }


# ---------------------------------------------------------------------------
# place_id 해석
# ---------------------------------------------------------------------------

def _resolve_place_id(url: str) -> str | None:
    """어떤 네이버 URL이든 place_id를 추출."""
    # 단축 URL 리다이렉트
    if "naver.me/" in url:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
            url = resp.url
        except Exception:
            pass

    place_id = _extract_place_id(url)
    if place_id:
        return place_id

    if _is_search_url(url):
        place_id = _resolve_place_id_via_requests(url)
        if place_id:
            return place_id
        # requests 실패 시 Playwright로 검색 결과에서 추출
        if _can_use_playwright():
            place_id = _resolve_place_id_via_browser(url)

    return place_id


def _resolve_place_id_via_browser(url: str) -> str | None:
    query = _extract_search_query(url)
    if not query:
        return None

    for q in _search_query_variants(query):
        search_url = f"https://m.search.naver.com/search.naver?query={quote(q)}"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(extra_http_headers=HEADERS)
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            anchors = page.locator("#place-main-section-root a[href*='m.place.naver.com']")
            href = None
            if anchors.count():
                href = anchors.first.get_attribute("href")
            browser.close()

        if href:
            place_id = _extract_place_id(href)
            if place_id:
                return place_id

    return None


# ---------------------------------------------------------------------------
# 공개 인터페이스
# ---------------------------------------------------------------------------

def crawl_naver_place(url: str) -> dict:
    if not url:
        raise ValueError("네이버 URL이 비어 있습니다.")

    place_id = _resolve_place_id(url)
    if not place_id:
        raise ValueError(f"Place ID를 추출할 수 없습니다: {url}")

    # 1차: GraphQL API (가장 정확)
    result = _fetch_via_graphql(place_id)
    if result:
        return result

    # 2차: HTML 파싱 fallback
    result = _fetch_via_html(place_id)
    if result:
        return result

    raise ValueError(f"평점/리뷰 정보를 가져오지 못했습니다. place_id={place_id}")
