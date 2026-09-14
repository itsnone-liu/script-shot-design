# -*- coding: utf-8 -*-
"""Point the creative index at the finished v2 master."""
import io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
p = Path(r'output\creative_v2\index.html')
s = p.read_text(encoding='utf-8')
if '成片' in s:
    print('index already updated'); raise SystemExit(0)
old = 'v2 选曲/剧本审阅页</a>'
new = 'v2 选曲/剧本审阅页</a> · <a href="concert30_v2_review.html">v2 成片《被卷进高潮》已出</a>'
if old in s:
    s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')
    print('index updated')
else:
    print('anchor not found; left unchanged')
