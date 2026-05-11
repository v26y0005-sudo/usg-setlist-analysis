# usg-setlist-analysis
# UNISON SQUARE GARDEN セットリスト・データセット

## 1. データの出典
- 出典元: [setlist.fm](https://www.setlist.fm/)
- 手法: setlist.fm REST API (v1.0) を使用した自動収集

## 2. 内容概要
日本のロックバンド「UNISON SQUARE GARDEN」の結成当時から現在に至るまでのセットリストデータを網羅したデータセットです。
- **取得したデータ数**: 15,897件（楽曲演奏単位）
- **項目**: 公演日、ツアー名、会場名、都市、演奏順、曲名
- **形式**: CSV形式（UTF-8-sig）

## 3. 取得コード
`usg_full_master.py` を実行することで、APIから最新のデータを再取得可能です。
※実行には `setlist.fm` のAPIキーが必要です。
