
for stock in stocks:
    params = {
        "q": _newsapi_query(stock),
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": _newsapi_page_size(),
        "apiKey": newsapi_key,
    }
    try:
        response = requests.get(NEWSAPI_URL, params=params, timeout=20)
        if response.status_code != 200:
            failed += 1
            print(f"[NewsAPI] ❌ {stock['ticker']} — HTTP {response.status_code}")
            continue

        payload = response.json() or {}
        rows = payload.get("articles") or []
        stock_new = 0

        for row in rows:
            normalized = _normalize_newsapi_article(row, stock)
            if not normalized:
                continue

            link = normalized["link"]
            if link in existing_links:
                skipped += 1
                continue

            existing_links.add(link)
            new_articles.append(normalized)
            stock_new += 1

        print(f"[NewsAPI] {stock['ticker']} — {stock_new} new")
    except Exception as e:
        failed += 1
        print(f"[NewsAPI] ❌ {stock['ticker']} — {e}")
