# -*- coding: utf-8 -*-
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URLS = [
    'https://zhuanlan.zhihu.com/p/1932431465095894723',
    'https://zhuanlan.zhihu.com/p/1978773717313143847?share_code=1jjRBHMxSvkuZ&utm_psn=2082107060095926840',
]
OUT = Path(__file__).resolve().parent / 'data' / 'zhihu_script_research'
OUT.mkdir(parents=True, exist_ok=True)

def main():
    with sync_playwright() as p:
        # Attach to the user's already-running visible Chrome, preserving its
        # real profile/session/network state. Do not create an anonymous context.
        browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        pages = context.pages
        page = next((p for p in pages if 'zhihu.com' in p.url), pages[-1] if pages else context.new_page())
        results=[]
        for i,url in enumerate(URLS,1):
            item={'url':url}
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=90000)
                page.wait_for_timeout(12000)
                item['title']=page.title()
                item['url_final']=page.url
                item['body_text']=page.locator('body').inner_text(timeout=15000)
                page.screenshot(path=str(OUT/f'article{i}.png'), full_page=True)
                item['html_length']=len(page.content())
                item['text_length']=len(item['body_text'])
                item['status']='ok'
                print(f'OK {i}: {item["title"]} text={item["text_length"]} final={item["url_final"]}')
            except Exception as e:
                item['status']='error'; item['error']=str(e)
                try: item['title']=page.title(); item['body_text']=page.locator('body').inner_text(timeout=5000)
                except Exception: pass
                print(f'FAIL {i}: {str(e)[:300]}')
            (OUT/f'article{i}.json').write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf-8')
            results.append(item)
        # This is the user's live Chrome process; disconnect without closing it.
        browser.disconnect()
    (OUT/'index.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__': main()
