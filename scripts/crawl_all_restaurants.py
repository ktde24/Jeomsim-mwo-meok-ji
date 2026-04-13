from pathlib import Path
import sys
import time


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from lunch_app.naver import crawl_naver_place
from lunch_app.repository import add_crawl_log, list_restaurants, save_metrics


def main() -> None:
    restaurants = list_restaurants()
    success = 0
    failed = 0
    for restaurant in restaurants:
        try:
            metrics = crawl_naver_place(restaurant["naver_url"])
            save_metrics(restaurant["id"], metrics)
            add_crawl_log(restaurant["id"], "success", "일괄 수집 성공")
            success += 1
            print(f"SUCCESS | {restaurant['name']} | {metrics.get('rating')} | {metrics.get('review_count')} | {metrics.get('congestion_text')}")
        except Exception as exc:
            add_crawl_log(restaurant["id"], "error", str(exc))
            failed += 1
            print(f"ERROR   | {restaurant['name']} | {exc}")
        time.sleep(0.35)

    print(f"\nDone. success={success} failed={failed}")


if __name__ == "__main__":
    main()
