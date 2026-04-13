from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from lunch_app.bootstrap import BASE_LOCATION_ADDRESS, BASE_LOCATION_NAME, seed_yeouido_restaurants
from lunch_app.repository import list_restaurants


def main() -> None:
    inserted = seed_yeouido_restaurants()
    restaurants = list_restaurants()
    print(f"Base location: {BASE_LOCATION_NAME} / {BASE_LOCATION_ADDRESS}")
    print(f"Seeded restaurants: {inserted}")
    print(f"Current restaurant rows: {len(restaurants)}")
    for restaurant in restaurants:
        print(
            f"- {restaurant['name']} | {restaurant['category']} | "
            f"{restaurant['distance_km']}km | {restaurant.get('naver_url') or '-'}"
        )


if __name__ == "__main__":
    main()
