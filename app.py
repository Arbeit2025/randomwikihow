"""ランダムWikiHow（randomwikihow）

ボタンを押すと、WikiHow からランダムで記事を1件表示するツール。
記事の取得はサーバー側で行う。WikiHow には MediaWiki の
Special:Random が無いため、ランダム記事へリダイレクトする
Special:Randomizer を使い、遷移先の記事ページから
タイトル（og:title）・概要（og:description）・画像（og:image）を抜き出す。
取得は日本語版（www.wikihow.jp）→ 英語版（www.wikihow.com）の順に試す。
WikiHow 側のボット対策（チャレンジページ等）でどちらも取得できない
場合は、WikiHow のランダム記事を直接開くボタンを表示する。
単一ファイル Flask。
"""
import html as html_lib
import os
import re
import urllib.request

from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# 取得は日本語版 → 英語版の順に試す
RANDOM_URLS = [
    "https://www.wikihow.jp/Special:Randomizer",
    "https://www.wikihow.com/Special:Randomizer",
]
# 最終URLがこのいずれかのままなら、記事ページへ遷移できていない
RANDOMIZER_URLS = {u.rstrip("/") for u in RANDOM_URLS}
DIRECT_RANDOM_URL = RANDOM_URLS[0]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
FETCH_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.9",
    "Referer": "https://www.wikihow.jp/",
}
FETCH_TIMEOUT = 15


def _og_content(html, prop):
    m = re.search(
        r'property="og:%s" content="([^"]*)"' % re.escape(prop), html
    )
    if not m:
        m = re.search(
            r'content="([^"]*)" property="og:%s"' % re.escape(prop), html
        )
    return html_lib.unescape(m.group(1)).strip() if m else ""


def clean_title(raw):
    """og:title から末尾の「 - wikiHow」を取り除く。"""
    title = raw.strip()
    if title.endswith(" - wikiHow"):
        title = title[: -len(" - wikiHow")]
    return title.strip()


def _fetch_from(random_url):
    """指定したランダマイザから記事を1件取得して dict で返す。

    次のいずれかに当たる場合は「記事を取得できなかった」として
    ValueError を送出する：
    - og:title が取れない
    - タイトルが空、またはチャレンジページの "Client Challenge" を含む
    - 最終URLがランダマイザのURL自体（記事ページへ遷移していない）
    """
    req = urllib.request.Request(random_url, headers=FETCH_HEADERS)
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as res:
        url = res.geturl()
        page = res.read().decode("utf-8", "replace")
    og_title = _og_content(page, "title")
    if not og_title:
        raise ValueError("missing og:title")
    title = clean_title(og_title)
    if not title or "Client Challenge" in title:
        raise ValueError("challenge page or empty title")
    if not url or url.rstrip("/") in RANDOMIZER_URLS:
        raise ValueError("randomizer did not redirect to an article page")
    return {
        "title": title,
        "description": _og_content(page, "description"),
        "thumbnail": _og_content(page, "image"),
        "url": url,
    }


def fetch_random_article():
    """WikiHow からランダムな記事を1件取得して dict で返す。

    日本語版 → 英語版の順に試す。どちらも取得できない場合は例外を
    送出する（呼び出し側でエラー表示＋直接開くボタンの表示にする）。
    """
    last_error = None
    for random_url in RANDOM_URLS:
        try:
            return _fetch_from(random_url)
        except Exception as exc:  # 次の候補を試す
            last_error = exc
    raise ValueError("could not fetch a random article") from last_error


PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ランダムWikiHow</title>
<style>
body{font-family:sans-serif;max-width:680px;margin:2em auto;padding:0 1em;color:#222}
h1{font-size:1.5em}
.bigbtn{display:inline-block;font-size:1.15em;padding:.7em 1.6em;margin:.6em 0;
background:#97ba5a;color:#fff;border:none;border-radius:8px;cursor:pointer}
.bigbtn:hover{background:#7ba344}
.card{border:1px solid #ccc;border-radius:10px;padding:1em 1.2em;margin-top:1em}
.card img{max-width:220px;max-height:220px;border-radius:6px;float:right;margin:0 0 .6em 1em}
.desc{line-height:1.7;white-space:pre-wrap}
.error{border:1px solid #d66;background:#fff3f3;border-radius:10px;padding:1em 1.2em;margin-top:1em}
a.read{font-weight:bold}
footer{margin-top:2em;color:#777;font-size:.85em}
</style>
</head><body>
<h1>🛠️ ランダムWikiHow</h1>
<p>ボタンを押すと、WikiHow の記事をランダムで1件表示します（日本語版を優先し、取得できない場合は英語版を表示します）。「やり方」との思わぬ出会いをどうぞ。</p>
<form method="get" action="/random">
  <button type="submit" class="bigbtn">🎲 ランダムで記事を表示</button>
</form>
{% if article %}
<div class="card">
  {% if article.thumbnail %}<img src="{{ article.thumbnail }}" alt="">{% endif %}
  <h2>{{ article.title }}</h2>
  {% if article.description %}<p class="desc">{{ article.description }}</p>{% endif %}
  <p><a class="read" href="{{ article.url }}" target="_blank" rel="noopener">記事を読む →</a></p>
</div>
{% elif error %}
<div class="error">
  <p>⚠️ {{ error }}</p>
  <p>WikiHow側の制限で、ここには直接表示できませんでした。下のボタンから直接開けます。</p>
  <p><a class="bigbtn" href="https://www.wikihow.jp/Special:Randomizer" target="_blank" rel="noopener">WikiHowで直接ランダム記事を開く</a></p>
</div>
{% endif %}
<footer>記事データ：<a href="https://www.wikihow.jp/" target="_blank" rel="noopener">日本語版 WikiHow</a></footer>
</body></html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE, article=None, error=None)


@app.route("/random")
def random_article():
    try:
        article = fetch_random_article()
    except Exception:
        return render_template_string(
            PAGE, article=None, error="記事を取得できませんでした。"
        )
    return render_template_string(PAGE, article=article, error=None)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
