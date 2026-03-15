---
name: fetch-news
description: 재테크 뉴스를 즉시 수집합니다
argument-hint: "[topic: all | stock_kr | stock_us | realestate | macro]"
user-invocable: true
allowed-tools:
  - Bash
---

다음 명령으로 재테크 뉴스를 즉시 수집합니다.

```bash
cd /Users/areum.k/playground/play/investment-news && python scripts/fetch_news.py $ARGUMENTS
```

인수 없이 실행하면 모든 카테고리를 수집합니다.
예시: `/fetch-news stock_kr` → 국내주식 뉴스만 수집
