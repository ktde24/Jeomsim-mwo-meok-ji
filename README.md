# Jeomsim-mwo-meok-ji

우리팀 내부용 점심 식당 추천 Streamlit 앱입니다.

## 기능

- 식당 등록 및 수정
- 거리/카테고리/혼잡도 기반 필터링
- 팀 방문 기록 및 개인 평점 저장
- 네이버 페이지 비공식 크롤링으로 평점/리뷰/혼잡 텍스트 갱신 시도
- 추천 점수 계산 후 오늘의 식당 추천

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 여의도 초기 데이터 재적재

```bash
python3 scripts/seed_yeouido.py
```

## 주의

- 네이버 페이지 구조가 바뀌면 크롤링 선택자가 깨질 수 있습니다.
- 혼잡도는 노출되지 않는 식당이 많아서 비어 있을 수 있습니다.
- 내부 팀용 MVP 기준으로 구현되어 인증/권한관리는 포함하지 않았습니다.
