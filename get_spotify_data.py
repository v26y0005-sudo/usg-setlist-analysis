import csv
import requests
import time
import os

# ==========================================
# 1. 日本語化済みマスターCSVの読み込み
# ==========================================
desktop_path = os.path.join(os.path.expanduser('~'), 'OneDrive', 'デスクトップ')

csv_path = os.path.join(desktop_path, 'usg_full_master_japanese.csv')
if not os.path.exists(csv_path):
    csv_path = 'usg_full_master_japanese.csv'

unique_songs = []
try:
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            song = row.get('Song')
            if song and song not in unique_songs:
                unique_songs.append(song)
    print(f"『{csv_path}』から {len(unique_songs)} 曲を読み込みました。")
except Exception as e:
    print(f"CSV読み込みエラー: {e}")
    print("デスクトップに 'usg_full_master_japanese.csv' があるか確認してください。")
    exit()

headers = {'User-Agent': 'USGDataCollector/1.0 ( test@example.com )'}
music_data = []

print("全曲の詳細メタデータを MusicBrainz から一括取得します...\n")

# ==========================================
# 2. 詳細データの取得
# ==========================================
for idx, song_name in enumerate(unique_songs, 1):
    query = f'recording:"{song_name}" AND artist:"UNISON SQUARE GARDEN"'
    url = f'https://musicbrainz.org/ws/2/recording?query={requests.utils.quote(query)}&fmt=json&limit=10'
    
    success = False
    retries = 0
    
    while not success and retries < 3:
        try:
            res = requests.get(url, headers=headers)
            
            if res.status_code == 503:
                retries += 1
                time.sleep(2.0)
                continue

            if res.status_code == 200:
                data = res.json()
                recordings = data.get('recordings', [])
                
                if recordings:
                    target_rec = None
                    # 長さ（length）がしっかり入っているものを優先
                    for rec in recordings:
                        if rec.get('length'):
                            target_rec = rec
                            break
                    if not target_rec:
                        target_rec = recordings[0]

                    # 秒数変換
                    length_ms = target_rec.get('length')
                    duration_sec = round(length_ms / 1000, 1) if length_ms else "不明"
                    
                    # 初出アルバム/シングル情報
                    releases = target_rec.get('releases', [])
                    first_album = "不明"
                    primary_type = "不明"
                    if releases:
                        rel = releases[0]
                        first_album = rel.get('title', '不明')
                        rel_group = rel.get('release-group', {})
                        primary_type = rel_group.get('primary-type', '不明')

                    # ISRCコード（複数ある場合は最初の一つ）
                    isrcs = target_rec.get('isrcs', [])
                    isrc_code = isrcs[0] if isrcs else "なし"

                    music_data.append({
                        'Song': song_name,
                        'MB_Track_Name': target_rec.get('title', '不明'),
                        'Duration_sec': duration_sec,
                        'First_Release_Date': target_rec.get('first-release-date', '不明'),
                        'Album_Name': first_album,
                        'Primary_Type': primary_type,
                        'ISRC': isrc_code,
                        'MBID': target_rec.get('id', '')
                    })
                    print(f"[{idx}/{len(unique_songs)}] 成功: {song_name} | {first_album} ({duration_sec}秒)")
                else:
                    music_data.append({
                        'Song': song_name,
                        'MB_Track_Name': '未発見',
                        'Duration_sec': '不明',
                        'First_Release_Date': '不明',
                        'Album_Name': '不明',
                        'Primary_Type': '不明',
                        'ISRC': 'なし',
                        'MBID': ''
                    })
                    print(f"[{idx}/{len(unique_songs)}] 未発見: {song_name}")
                
                success = True
            else:
                print(f"[{idx}/{len(unique_songs)}] エラー ({res.status_code}): {song_name}")
                success = True

        except Exception as e:
            print(f"[{idx}/{len(unique_songs)}] 通信エラー ({song_name}): {e}")
            time.sleep(2.0)
            retries += 1

    time.sleep(1.2)

# ==========================================
# 3. CSV出力
# ==========================================
output_path = os.path.join(desktop_path, 'usg_features.csv')
fieldnames = [
    'Song', 
    'MB_Track_Name', 
    'Duration_sec', 
    'First_Release_Date', 
    'Album_Name', 
    'Primary_Type', 
    'ISRC', 
    'MBID'
]

with open(output_path, mode='w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(music_data)

print(f"\n完了！ すべてのメタデータを '{output_path}' に保存しました。")