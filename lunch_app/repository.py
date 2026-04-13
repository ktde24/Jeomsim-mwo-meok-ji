from __future__ import annotations

from datetime import date, timedelta

from lunch_app.db import get_connection


def list_restaurants() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                r.*,
                m.rating,
                m.review_count,
                m.congestion_text,
                m.congestion_score,
                m.crawled_at,
                COALESCE(AVG(v.user_rating), 0) AS team_rating,
                COUNT(v.id) AS visit_count,
                MAX(v.visited_on) AS last_visited_on
            FROM restaurants r
            LEFT JOIN restaurant_metrics m ON m.restaurant_id = r.id
            LEFT JOIN visits v ON v.restaurant_id = r.id
            GROUP BY r.id
            ORDER BY r.name COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_restaurant(restaurant_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                r.*,
                m.rating,
                m.review_count,
                m.congestion_text,
                m.congestion_score,
                m.crawled_at
            FROM restaurants r
            LEFT JOIN restaurant_metrics m ON m.restaurant_id = r.id
            WHERE r.id = ?
            """,
            (restaurant_id,),
        ).fetchone()
    return dict(row) if row else None


def add_restaurant(payload: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO restaurants
            (name, category, distance_km, address, naver_url, price_level, tags, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["name"],
                payload["category"],
                payload["distance_km"],
                payload.get("address"),
                payload.get("naver_url"),
                payload.get("price_level"),
                payload.get("tags"),
                payload.get("note"),
            ),
        )


def upsert_restaurant_by_name(payload: dict) -> int:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM restaurants WHERE name = ?",
            (payload["name"],),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE restaurants
                SET category = ?, distance_km = ?, address = ?, naver_url = ?,
                    price_level = ?, tags = ?, note = ?
                WHERE id = ?
                """,
                (
                    payload["category"],
                    payload["distance_km"],
                    payload.get("address"),
                    payload.get("naver_url"),
                    payload.get("price_level"),
                    payload.get("tags"),
                    payload.get("note"),
                    existing["id"],
                ),
            )
            return int(existing["id"])

        cursor = conn.execute(
            """
            INSERT INTO restaurants
            (name, category, distance_km, address, naver_url, price_level, tags, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["name"],
                payload["category"],
                payload["distance_km"],
                payload.get("address"),
                payload.get("naver_url"),
                payload.get("price_level"),
                payload.get("tags"),
                payload.get("note"),
            ),
        )
        return int(cursor.lastrowid)


def update_restaurant(restaurant_id: int, payload: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE restaurants
            SET name = ?, category = ?, distance_km = ?, address = ?, naver_url = ?,
                price_level = ?, tags = ?, note = ?
            WHERE id = ?
            """,
            (
                payload["name"],
                payload["category"],
                payload["distance_km"],
                payload.get("address"),
                payload.get("naver_url"),
                payload.get("price_level"),
                payload.get("tags"),
                payload.get("note"),
                restaurant_id,
            ),
        )


def save_metrics(restaurant_id: int, metrics: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO restaurant_metrics
            (restaurant_id, rating, review_count, congestion_text, congestion_score, crawled_at, raw_summary, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(restaurant_id) DO UPDATE SET
                rating = excluded.rating,
                review_count = excluded.review_count,
                congestion_text = excluded.congestion_text,
                congestion_score = excluded.congestion_score,
                crawled_at = excluded.crawled_at,
                raw_summary = excluded.raw_summary,
                source = excluded.source
            """,
            (
                restaurant_id,
                metrics.get("rating"),
                metrics.get("review_count"),
                metrics.get("congestion_text"),
                metrics.get("congestion_score"),
                metrics.get("crawled_at"),
                metrics.get("raw_summary"),
                metrics.get("source", "naver"),
            ),
        )


def add_crawl_log(restaurant_id: int, status: str, message: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO crawl_logs (restaurant_id, status, message)
            VALUES (?, ?, ?)
            """,
            (restaurant_id, status, message),
        )


def list_recent_logs(limit: int = 30) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                l.*,
                r.name AS restaurant_name
            FROM crawl_logs l
            JOIN restaurants r ON r.id = l.restaurant_id
            ORDER BY l.crawled_at DESC, l.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def add_visit(payload: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO visits (restaurant_id, user_name, visited_on, user_rating, memo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload["restaurant_id"],
                payload["user_name"],
                payload["visited_on"],
                payload.get("user_rating"),
                payload.get("memo"),
            ),
        )


def list_visits(limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                v.*,
                r.name AS restaurant_name,
                r.category
            FROM visits v
            JOIN restaurants r ON r.id = v.restaurant_id
            ORDER BY v.visited_on DESC, v.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_yesterday_categories() -> set[str]:
    """어제 팀이 방문한 카테고리 목록 반환."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT r.category
            FROM visits v
            JOIN restaurants r ON r.id = v.restaurant_id
            WHERE v.visited_on = ?
            """,
            (yesterday,),
        ).fetchall()
    return {row["category"] for row in rows}


def delete_restaurants_by_names(names: list[str]) -> None:
    if not names:
        return

    placeholders = ",".join("?" for _ in names)
    with get_connection() as conn:
        restaurant_rows = conn.execute(
            f"SELECT id FROM restaurants WHERE name IN ({placeholders})",
            tuple(names),
        ).fetchall()
        restaurant_ids = [row["id"] for row in restaurant_rows]
        if not restaurant_ids:
            return

        id_placeholders = ",".join("?" for _ in restaurant_ids)
        conn.execute(f"DELETE FROM crawl_logs WHERE restaurant_id IN ({id_placeholders})", tuple(restaurant_ids))
        conn.execute(f"DELETE FROM visits WHERE restaurant_id IN ({id_placeholders})", tuple(restaurant_ids))
        conn.execute(f"DELETE FROM restaurant_metrics WHERE restaurant_id IN ({id_placeholders})", tuple(restaurant_ids))
        conn.execute(f"DELETE FROM restaurants WHERE id IN ({id_placeholders})", tuple(restaurant_ids))


def seed_demo_data() -> None:
    if list_restaurants():
        return

    demo_restaurants = [
        {
            "name": "을지국밥",
            "category": "한식",
            "distance_km": 0.4,
            "address": "회사 근처 골목 12",
            "naver_url": "",
            "price_level": "10000~15000원",
            "tags": "국밥,혼밥",
            "note": "회전 빠름",
        },
        {
            "name": "사쿠라동",
            "category": "일식",
            "distance_km": 0.9,
            "address": "대로변 22",
            "naver_url": "",
            "price_level": "12000~18000원",
            "tags": "덮밥,우동",
            "note": "점심에 웨이팅 조금 있음",
        },
        {
            "name": "포메이트",
            "category": "베트남",
            "distance_km": 1.8,
            "address": "오피스몰 B1",
            "naver_url": "",
            "price_level": "11000~16000원",
            "tags": "쌀국수,반미",
            "note": "국물 깔끔",
        },
    ]

    for restaurant in demo_restaurants:
        add_restaurant(restaurant)

    restaurants = list_restaurants()
    today = date.today().isoformat()
    for row in restaurants:
        save_metrics(
            row["id"],
            {
                "rating": 4.3,
                "review_count": 120,
                "congestion_text": "보통",
                "congestion_score": 2,
                "crawled_at": f"{today} 12:00:00",
                "raw_summary": "demo data",
            },
        )
