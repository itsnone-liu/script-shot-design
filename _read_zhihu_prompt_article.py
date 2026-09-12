# -*- coding: utf-8 -*-
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
URL='https://zhuanlan.zhihu.com/p/2081778327027827939?share_code=1SxGWp2a6dzy&utm_psn=2082156176293238052'
OUT=Path(__file__).resolve().parent/'data'/'zhihu_prompt_research'
OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context=browser.contexts[0]
    pages=context.pages
    page=next((x for x in pages if 'zhihu.com' in x.url),pages[-1] if pages else context.new_page())
    item={'url':URL}
    try:
        page.goto(URL,wait_until='domcontentloaded',timeout=90000)
        page.wait_for_timeout(12000)
        item.update(status='ok',title=page.title(),url_final=page.url,body_text=page.locator('body').inner_text(timeout=15000),html_length=len(page.content()))
        page.screenshot(path=str(OUT/'article.png'),full_page=True)
    except Exception as e:
        item.update(status='error',error=str(e))
        try:item.update(title=page.title(),url_final=page.url,body_text=page.locator('body').inner_text(timeout=5000))
        except Exception:pass
    (OUT/'article.json').write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:item.get(k) for k in ('status','title','url_final','html_length')},ensure_ascii=False))
    # Playwright Python has no Browser.disconnect(); leaving the CDP-attached
    # browser unclosed preserves the user's live Chrome session.
