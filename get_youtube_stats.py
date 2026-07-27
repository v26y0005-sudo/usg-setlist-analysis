import csv
import os
import time
import requests
import re

# ==========================================
# 1. APIキーの設定
# ==========================================
YOUTUBE_API_KEY = "AIzaSyC8Di43DEhmiAE9WgNFtY5zK6Re3hJl7qM"

# UNISON SQUARE GARDEN 公式チャンネルID
CHANNEL_ID = "UCy6p-dIbgL3A8K_e6sP1-lQ"

# ==========================================
# 2. 日本語マスターCSVの読み込み
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
    exit()

# ==========================================
# 3. 公式チャンネルの「アップロード再生リストID」取得
# ==========================================
print("\n[ステップ1] 公式チャンネルから全動画リストを一括取得中...")

ch_url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={CHANNEL_ID}&key={YOUTUBE_API_KEY}"
ch_res = requests.get(ch_url).json()

uploads_playlist_id = None
try:
    uploads_playlist_id = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
except (KeyError, IndexError):
    handle_url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&forHandle=unisonsgofficial&key={YOUTUBE_API_KEY}"
    handle_res = requests.get(handle_url).json()
    try:
        uploads_playlist_id = handle_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    except (KeyError, IndexError):
        print("チャンネル情報の取得に失敗しました。APIキーを確認してください。")
        exit()

all_channel_videos = []
next_page_token = ""

while True:
    pl_url = (
        f"https://www.googleapis.com/youtube/v3/playlistItems"
        f"?part=snippet&playlistId={uploads_playlist_id}&maxResults=50"
        f"&pageToken={next_page_token}&key={YOUTUBE_API_KEY}"
    )
    pl_res = requests.get(pl_url).json()
    items = pl_res.get('items', [])
    
    for item in items:
        snippet = item.get('snippet', {})
        resource_id = snippet.get('resourceId', {})
        if resource_id.get('kind') == 'youtube#video':
            all_channel_videos.append({
                'video_id': resource_id.get('videoId'),
                'title': snippet.get('title', ''),
                'published_at': snippet.get('publishedAt', '')[:10]
            })

    next_page_token = pl_res.get('nextPageToken')
    if not next_page_token:
        break
    time.sleep(0.1)

print(f" └ 公式チャンネルから計 {len(all_channel_videos)} 件の動画を取得完了。")

# ==========================================
# 4. タイトル照合判定関数
# ==========================================
def is_song_in_title(song_name, video_title):
    title_raw = video_title
    song_raw = song_name.strip()
    
    if song_raw == "5%":
        return bool(re.search(r'(?<!\d)5%', title_raw))
        
    clean_song = re.sub(r'[^a-zA-Z0-9ぁ-んァ-ヶ亜-黑]', '', song_raw).lower()
    clean_title = re.sub(r'[^a-zA-Z0-9ぁ-んァ-ヶ亜-黑]', '', title_raw).lower()
    
    if len(clean_song) <= 3:
        pattern = r'[\"「『\s]' + re.escape(song_raw) + r'[\"」』\s]'
        if re.search(pattern, title_raw) or song_raw == title_raw:
            return True
        return clean_song == clean_title

    return clean_song in clean_title

# ==========================================
# 5. 高精度なMV / Live動画分離処理
# ==========================================
print("\n[ステップ2] ライブ映像とMVを高精度に照合・分類中...")

song_video_map = {}
target_video_ids = set()

for song in unique_songs:
    candidate_mv = None
    candidate_other = None

    for vid_info in all_channel_videos:
        title = vid_info['title']
        title_upper = title.upper()
        
        # ショート動画・ティザー動画のスキップ
        if "SHORT" in title_upper or "#" in title or "ショート" in title:
            continue
        if "ティザー" in title or "TEASER" in title_upper or "SPOT" in title_upper or "クロスフェード" in title:
            continue

        # 曲名が含まれているか確認
        if is_song_in_title(song, title):
            has_mv_kw = ("MV" in title_upper or "MUSIC VIDEO" in title_upper or "ミュージックビデオ" in title)
            has_live_kw = ("LIVE" in title_upper or "ライブ" in title_upper or "FROM" in title_upper or "AT" in title_upper or "TOUR" in title_upper)

            # 「LIVE MUSIC VIDEO」や ライブ情報(from...)が含まれる場合はライブ映像枠(Other)へ
            if has_live_kw:
                if not candidate_other:
                    candidate_other = vid_info
                    target_video_ids.add(vid_info['video_id'])
            # ライブキーがなく、MVキーワードがある純粋なMV
            elif has_mv_kw:
                if not candidate_mv:
                    candidate_mv = vid_info
                    target_video_ids.add(vid_info['video_id'])
            # どちらのキーワードも無いがタイトルが一致している場合は、Otherのフォールバックとして保持
            else:
                if not candidate_other:
                    candidate_other = vid_info
                    target_video_ids.add(vid_info['video_id'])

    song_video_map[song] = {
        'mv': candidate_mv,
        'other': candidate_other
    }

# ==========================================
# 6. 動画IDから詳細情報（Statistics）を一括取得
# ==========================================
print(f"\n[ステップ3] 該当する {len(target_video_ids)} 件の動画の統計数を取得中...")

video_stats_map = {}
target_ids_list = list(target_video_ids)

for i in range(0, len(target_ids_list), 50):
    chunk = target_ids_list[i:i+50]
    ids_str = ",".join(chunk)
    
    stats_url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=statistics&id={ids_str}&key={YOUTUBE_API_KEY}"
    )
    stats_res = requests.get(stats_url).json()
    
    for item in stats_res.get('items', []):
        vid = item['id']
        st = item.get('statistics', {})
        video_stats_map[vid] = {
            'views': st.get('viewCount', '0'),
            'likes': st.get('likeCount', '0'),
            'comments': st.get('commentCount', '0')
        }
    time.sleep(0.1)

# ==========================================
# 7. データの統合と出力処理
# ==========================================
youtube_data = []

for song in unique_songs:
    mv_v = song_video_map[song]['mv']
    other_v = song_video_map[song]['other']

    if mv_v and mv_v['video_id'] in video_stats_map:
        st = video_stats_map[mv_v['video_id']]
        mv_res = {
            'title': mv_v['title'], 'views': st['views'], 'likes': st['likes'],
            'comments': st['comments'], 'pub': mv_v['published_at'],
            'url': f"https://www.youtube.com/watch?v={mv_v['video_id']}"
        }
    else:
        mv_res = {'title': '未発見', 'views': '0', 'likes': '0', 'comments': '0', 'pub': '', 'url': ''}

    if other_v and other_v['video_id'] in video_stats_map:
        st = video_stats_map[other_v['video_id']]
        other_res = {
            'title': other_v['title'], 'views': st['views'], 'likes': st['likes'],
            'comments': st['comments'], 'pub': other_v['published_at'],
            'url': f"https://www.youtube.com/watch?v={other_v['video_id']}"
        }
    else:
        other_res = {'title': '未発見', 'views': '0', 'likes': '0', 'comments': '0', 'pub': '', 'url': ''}

    youtube_data.append({
        'Song': song,
        'MV_Video_Title': mv_res['title'],
        'MV_View_Count': mv_res['views'],
        'MV_Like_Count': mv_res['likes'],
        'MV_Comment_Count': mv_res['comments'],
        'MV_Published_At': mv_res['pub'],
        'MV_URL': mv_res['url'],
        'Other_Video_Title': other_res['title'],
        'Other_View_Count': other_res['views'],
        'Other_Like_Count': other_res['likes'],
        'Other_Comment_Count': other_res['comments'],
        'Other_Published_At': other_res['pub'],
        'Other_URL': other_res['url'],
    })

# ==========================================
# 8. CSV出力
# ==========================================
output_path = os.path.join(desktop_path, 'usg_youtube_stats.csv')
fieldnames = [
    'Song', 
    'MV_Video_Title', 'MV_View_Count', 'MV_Like_Count', 'MV_Comment_Count', 'MV_Published_At', 'MV_URL',
    'Other_Video_Title', 'Other_View_Count', 'Other_Like_Count', 'Other_Comment_Count', 'Other_Published_At', 'Other_URL'
]

with open(output_path, mode='w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(youtube_data)

print(f"\n完了！ ライブ映像の検出精度を大幅に向上させた最新データを '{output_path}' に保存しました。")