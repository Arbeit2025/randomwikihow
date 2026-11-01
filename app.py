"""ランダムWikiHow（randomwikihow）

ボタンを押すと、日本語版 WikiHow（www.wikihow.jp）から
ランダムで記事を1件表示するツール。
記事の取得はサーバー側で行う。WikiHow には MediaWiki の
Special:Random が無いため、ランダム記事へリダイレクトする
Special:Randomizer を使い、遷移先の記事ページから
タイトル（og:title）・概要（og:description）・画像（og:image）を抜き出す。
単一ファイル Flask。
"""
import html as html_lib
import os
import re
import urllib.request

from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

RANDOM_URL = "https://www.wikihow.jp/Special:Randomizer"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
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


def fetch_random_article():
    """WikiHow（日本語版）からランダムな記事を1件取得して dict で返す。

    取得できない場合は例外を送出する（呼び出し側でエラー表示にする）。
    """
    req = urllib.request.Request(RANDOM_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as res:
        url = res.geturl()
        html = res.read().decode("utf-8", "replace")
    title = clean_title(_og_content(html, "title"))
    if not title:
        m = re.search(r"<title>([^<]+)</title>", html)
        title = clean_title(m.group(1)) if m else ""
    if not title or not url:
        raise ValueError("could not parse article page")
    return {
        "title": title,
        "description": _og_content(html, "description"),
        "thumbnail": _og_content(html, "image"),
        "url": url,
    }


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
<p>ボタンを押すと、日本語版 WikiHow の記事をランダムで1件表示します。「やり方」との思わぬ出会いをどうぞ。</p>
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
  <p>通信がうまくいかなかったようです。もう一度ボタンを押してみてください。</p>
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
