import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as app_module  # noqa: E402

SAMPLE = {
    "title": "テストのやり方 3つの方法",
    "description": "これはテスト記事の概要です。",
    "thumbnail": "https://www.wikihow.com/images/sample.jpg",
    "url": "https://www.wikihow.jp/テストのやり方",
}


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
