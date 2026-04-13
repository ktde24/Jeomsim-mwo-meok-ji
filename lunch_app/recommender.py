from __future__ import annotations

from datetime import date, datetime


def _distance_score(distance_km: float) -> float:
    if distance_km <= 1:
        return 3.0
    if distance_km <= 3:
        return 2.0
    if distance_km <= 5:
        return 1.0
    return -2.0


def _congestion_adjustment(score: int | None) -> float:
    if score is None:
        return 0.0
    return {1: 2.0, 2: 0.5, 3: -2.0}.get(score, 0.0)


def _recent_visit_penalty(last_visited_on: str | None) -> float:
    if not last_visited_on:
        return 1.0
    days = (date.today() - datetime.fromisoformat(last_visited_on).date()).days
    if days <= 3:
        return -4.0
    if days <= 7:
        return -2.0
    if days <= 14:
        return -0.5
    return 1.0


def _visit_count_penalty(visit_count: int) -> float:
    if visit_count >= 8:
        return -2.5
    if visit_count >= 5:
        return -1.5
    if visit_count >= 3:
        return -0.5
    return 0.5


def score_restaurant(restaurant: dict) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    distance_component = _distance_score(float(restaurant["distance_km"]))
    score += distance_component
    if distance_component >= 2:
        reasons.append("가까운 거리")

    naver_rating = restaurant.get("rating") or 0
    rating_component = float(naver_rating) * 0.9
    score += rating_component
    if naver_rating:
        reasons.append(f"네이버 평점 {naver_rating}")

    team_rating = restaurant.get("team_rating") or 0
    if team_rating:
        score += float(team_rating) * 0.8
        reasons.append(f"팀 평점 {team_rating:.1f}")

    congestion_component = _congestion_adjustment(restaurant.get("congestion_score"))
    score += congestion_component
    if congestion_component > 0:
        reasons.append("혼잡도 무난")
    elif congestion_component < 0:
        reasons.append("혼잡 가능성 높음")

    recency_component = _recent_visit_penalty(restaurant.get("last_visited_on"))
    score += recency_component
    if recency_component > 0:
        reasons.append("최근에 덜 감")

    visit_component = _visit_count_penalty(int(restaurant.get("visit_count") or 0))
    score += visit_component
    if visit_component > 0:
        reasons.append("반복 방문 적음")

    return score, reasons


def recommend(restaurants: list[dict]) -> list[dict]:
    scored = []
    for restaurant in restaurants:
        score, reasons = score_restaurant(restaurant)
        enriched = dict(restaurant)
        enriched["recommendation_score"] = round(score, 2)
        enriched["recommendation_reasons"] = reasons[:4]
        scored.append(enriched)
    return sorted(scored, key=lambda item: item["recommendation_score"], reverse=True)
