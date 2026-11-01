# ランダムWikiHow（randomwikihow）

ボタンを押すと、日本語版 WikiHow の記事をランダムで1件表示する小さなツールです。

## 使い方

- **🎲 ランダムで記事を表示**：日本語版 WikiHow（www.wikihow.jp）からランダムな記事を1件取得し、タイトル・概要・サムネイル（あれば）を表示します。
- **記事を読む**：その記事の WikiHow ページを新しいタブで開きます。
- もう一度ボタンを押すと、別の記事が表示されます。

## 仕組み

記事の取得はサーバー側で行います。WikiHow には MediaWiki の `Special:Random` が無いため、ランダム記事へリダイレクトする `https://www.wikihow.jp/Special:Randomizer` を使い、遷移先の記事ページの OGP 情報（og:title / og:description / og:image）からタイトル・概要・画像を抜き出して表示します。通信に失敗した場合はエラーメッセージと再試行ボタンが表示されます。

## ローカル実行

```bash
pip install -r requirements.txt
python app.py
# http://localhost:5000
```

## テスト

```bash
python -m unittest discover -s tests
```

※ テストでは外部通信を行わず、取得処理をモックに差し替えて検証します。

## Render へのデプロイ

`render.yaml` 同梱。無料プラン（free）の Web Service としてデプロイできます（healthCheckPath: `/healthz`）。
