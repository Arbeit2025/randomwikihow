import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as app_module  # noqa: E402

SAMPLE = {
    "title": "テストのやり方 3つの方法",
    "description": "これはテスト記事の概要です。",
    "thumbnail": "https://www.wikihow.com/images/sample.jpg",
    "url": "https://www.wikihow.jp/テストのやり方",
}

# WikiHow 側のボット対策が返すチャレンジページの模擬HTML
CHALLENGE_HTML = (
    "<!doctype html><html><head>"
    "<title>Client Challenge</title>"
    '<meta property="og:title" content="Client Challenge">'
    "</head><body>Please verify you are a human.</body></html>"
)

# 英語版の正常な記事ページの模擬HTML
EN_ARTICLE_HTML = (
    "<!doctype html><html><head>"
    '<meta property="og:title" content="How to Test Things: 3 Steps - wikiHow">'
    '<meta property="og:description" content="An English sample article.">'
    '<meta property="og:image" content="https://www.wikihow.com/images/en-sample.jpg">'
    "</head><body>article body</body></html>"
)
EN_ARTICLE_URL = "https://www.wikihow.com/Test-Things"

# og:title の無いページ（<title> だけある）の模擬HTML
NO_OG_HTML = (
    "<!doctype html><html><head>"
    "<title>題名だけのページ - wikiHow</title>"
    "</head><body>no og tags</body></html>"
)


class FakeResponse:
    """urlopen の戻り値の代役。最終URLと本文を固定で返す。"""

    def __init__(self, url, body):
        self._url = url
        self._body = body.encode("utf-8")

    def geturl(self):
        return self._url

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class RandomWikiHowTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self._orig_fetch = app_module.fetch_random_article

    def tearDown(self):
        app_module.fetch_random_article = self._orig_fetch

    def test_healthz(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "ok")

    def test_index_ok(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("ランダムWikiHow", body)
        self.assertIn("ランダムで記事を表示", body)

    def test_random_success(self):
        app_module.fetch_random_article = lambda: dict(SAMPLE)
        res = self.client.get("/random")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("テストのやり方 3つの方法", body)
        self.assertIn("これはテスト記事の概要です。", body)
        self.assertIn("https://www.wikihow.com/images/sample.jpg", body)
        self.assertIn("https://www.wikihow.jp/テストのやり方", body)
        self.assertIn("記事を読む", body)

    def test_random_success_without_thumbnail(self):
        article = dict(SAMPLE)
        article["thumbnail"] = ""
        article["description"] = ""
        app_module.fetch_random_article = lambda: article
        res = self.client.get("/random")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("テストのやり方 3つの方法", body)
        self.assertNotIn("sample.jpg", body)

    def test_random_failure_shows_error(self):
        def boom():
            raise RuntimeError("network down")

        app_module.fetch_random_article = boom
        res = self.client.get("/random")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("記事を取得できませんでした", body)
        self.assertIn("ランダムで記事を表示", body)

    def test_challenge_page_not_shown_as_article(self):
        # どちらのランダマイザもチャレンジページを返し、最終URLも
        # ランダマイザのまま（記事へ遷移していない）ケース
        def fake_urlopen(req, timeout=None):
            return FakeResponse(req.full_url, CHALLENGE_HTML)

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            res = self.client.get("/random")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        # チャレンジが「記事」として表示されていないこと
        self.assertNotIn("Client Challenge", body)
        self.assertNotIn('class="card"', body)
        # エラー＋直接開くフォールバックボタンが出ること
        self.assertIn("記事を取得できませんでした", body)
        self.assertIn("WikiHowで直接ランダム記事を開く", body)
        self.assertIn("https://www.wikihow.jp/Special:Randomizer", body)

    def test_fetch_falls_back_to_english_wikihow(self):
        # 日本語版はチャレンジ、英語版は正常な記事を返すケース
        def fake_urlopen(req, timeout=None):
            if "wikihow.jp" in req.full_url:
                return FakeResponse(req.full_url, CHALLENGE_HTML)
            return FakeResponse(EN_ARTICLE_URL, EN_ARTICLE_HTML)

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            res = self.client.get("/random")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("How to Test Things: 3 Steps", body)
        self.assertIn("An English sample article.", body)
        self.assertIn("https://www.wikihow.com/images/en-sample.jpg", body)
        self.assertIn(EN_ARTICLE_URL, body)
        self.assertIn("記事を読む", body)

    def test_missing_og_title_is_failure(self):
        # og:title が取れないページは記事として扱わず失敗にする
        def fake_urlopen(req, timeout=None):
            return FakeResponse(EN_ARTICLE_URL, NO_OG_HTML)

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            with self.assertRaises(ValueError):
                app_module.fetch_random_article()
            res = self.client.get("/random")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertNotIn('class="card"', body)
        self.assertIn("WikiHowで直接ランダム記事を開く", body)

    def test_clean_title(self):
        self.assertEqual(
            app_module.clean_title("ヘビと信頼関係を築く 3つの方法 - wikiHow"),
            "ヘビと信頼関係を築く 3つの方法",
        )
        self.assertEqual(app_module.clean_title("そのままの題名"), "そのままの題名")

    def test_og_content(self):
        html = '<meta property="og:title" content="題名テスト">'
        self.assertEqual(app_module._og_content(html, "title"), "題名テスト")
        self.assertEqual(app_module._og_content(html, "image"), "")

    def test_og_content_unescapes_entities(self):
        html = '<meta property="og:title" content="赤&amp;白ワイン">'
        self.assertEqual(app_module._og_content(html, "title"), "赤&白ワイン")


if __name__ == "__main__":
    unittest.main()
