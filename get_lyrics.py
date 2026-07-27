import csv
import os
import time
import requests
from bs4 import BeautifulSoup
import re

desktop_path = os.path.join(os.path.expanduser('~'), 'OneDrive', 'デスクトップ')
csv_path = os.path.join(desktop_path, 'usg_full_master_japanese.csv')

if not os.path.exists(csv_path):
    csv_path = 'usg_full_master_japanese.csv'

# 1. マスターCSVの曲名をセットにする（表記比較用）
master_songs = {}
try:
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            s = row.get('Song', '').strip()
            if s:
                # 比較用に小文字・記号除去したキーを作成
                clean_k = re.sub(r'[^a-zA-Z0-9ぁ-んァ-ヶ亜-黑]', '', s).lower()
                master_songs[clean_k] = s
    print(f"『{csv_path}』から {len(master_songs)} 曲のリストを準備しました。")
except Exception as e:
    print(f"CSV読み込みエラー: {e}")
    exit()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ==========================================
# 2. UNISON SQUARE GARDENの全曲一覧ページからURLを一括収集
# ==========================================
print("\n[ステップ1] 歌ネットのUNISON SQUARE GARDEN楽曲一覧からURLを取得中...")

# 歌ネットのUNISON SQUARE GARDEN アーティストページ (AID=8377)
artist_url = "https://www.uta-net.com/artist/8377/"
song_url_map = {}

try:
    res = requests.get(artist_url, headers=headers)
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, 'html.parser')
        # 楽曲リンクを探索
        for a in soup.find_all('a', href=True):
            if '/song/' in a['href']:
                title = a.get_text().strip()
                full_url = "https://www.uta-net.com" + a['href']
                clean_t = re.sub(r'[^a-zA-Z0-9ぁ-んァ-ヶ亜-黑]', '', title).lower()
                song_url_map[clean_t] = (title, full_url)
        print(f"歌ネット上で {len(song_url_map)} 曲のリンクを発見しました！")
    else:
        print(f"アーティストページの取得に失敗しました (Status: {res.status_code})")
        exit()
except Exception as e:
    print(f"通信エラー: {e}")
    exit()

# ==========================================
# 3. 順次アクセスして歌詞を抽出
# ==========================================
print("\n[ステップ2] 各楽曲ページから歌詞を順次取得します（マナーモード: 2秒間隔）...\n")

lyrics_data = []
total_songs = len(master_songs)

for idx, (clean_k, original_song) in enumerate(master_songs.items(), 1):
    # 歌ネットの一覧から一致する曲のURLを探す
    matched_info = song_url_map.get(clean_k)
    
    # 完全一致しない場合の部分一致リカバリ
    if not matched_info:
        for k, v in song_url_map.items():
            if clean_k in k or k in clean_k:
                matched_info = v
                break

    if matched_info:
        song_title_utanet, song_url = matched_info
        try:
            time.sleep(5.0)  # サーバー負荷防止用ウェイト
            page_res = requests.get(song_url, headers=headers)
            
            if page_res.status_code == 200:
                page_soup = BeautifulSoup(page_res.text, 'html.parser')
                kashi_area = page_soup.find('div', id='kashi_area')
                
                if kashi_area:
                    for br in kashi_area.find_all("br"):
                        br.replace_with("\n")
                    lyrics_text = kashi_area.get_text().strip()
                    
                    lyrics_data.append({
                        'Song': original_song,
                        'UtaNet_Title': song_title_utanet,
                        'Lyrics': lyrics_text,
                        'URL': song_url
                    })
                    print(f"[{idx}/{total_songs}] 成功: {original_song}")
                else:
                    lyrics_data.append({'Song': original_song, 'UtaNet_Title': song_title_utanet, 'Lyrics': '歌詞枠未発見', 'URL': song_url})
                    print(f"[{idx}/{total_songs}] 歌詞テキスト取得失敗: {original_song}")
            else:
                lyrics_data.append({'Song': original_song, 'UtaNet_Title': song_title_utanet, 'Lyrics': 'ページ取得失敗', 'URL': song_url})
                print(f"[{idx}/{total_songs}] ページエラー ({page_res.status_code}): {original_song}")

        except Exception as e:
            lyrics_data.append({'Song': original_song, 'UtaNet_Title': '', 'Lyrics': '通信エラー', 'URL': ''})
            print(f"[{idx}/{total_songs}] 通信エラー ({original_song}): {e}")
    else:
        lyrics_data.append({'Song': original_song, 'UtaNet_Title': '未掲載', 'Lyrics': '未発見', 'URL': ''})
        print(f"[{idx}/{total_songs}] 歌ネット未掲載: {original_song}")

# ==========================================
# 4. CSV出力
# ==========================================
output_path = os.path.join(desktop_path, 'usg_lyrics.csv')
fieldnames = ['Song', 'UtaNet_Title', 'Lyrics', 'URL']

with open(output_path, mode='w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(lyrics_data)

print(f"\n完了！ 歌詞データを '{output_path}' に保存しました。")