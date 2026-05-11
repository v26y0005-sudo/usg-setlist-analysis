import requests
import pandas as pd
import time

# --- 設定 ---
API_KEY = "50rb_xloAeNlys9rY3tdh0beDyyeNY4-CxkB"
MBID = "265a2fb6-dde5-48d3-9e6e-47708aa5e10a" # UNISON SQUARE GARDEN
HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json"
}

def get_all_usg_setlists():
    all_data = []
    # 1ページ目からデータがなくなるまでループ
    for page in range(1, 151):
        print(f"Fetching page {page} from setlist.fm...")
        url = f"https://api.setlist.fm/rest/1.0/artist/{MBID}/setlists?p={page}"
        
        try:
            response = requests.get(url, headers=HEADERS)
            
            if response.status_code == 200:
                data = response.json()
                setlists = data.get('setlist', [])
                if not setlists:
                    break

                for sl in setlists:
                    event_date = sl.get('eventDate')
                    venue_name = sl.get('venue', {}).get('name', 'Unknown')
                    city = sl.get('venue', {}).get('city', {}).get('name', 'Unknown')
                    # ツアー名を取得
                    tour_name = sl.get('tour', {}).get('name', 'No Tour Data')
                    
                    sets = sl.get('sets', {}).get('set', [])
                    song_count = 1
                    for s in sets:
                        for song in s.get('song', []):
                            all_data.append({
                                'Date': event_date,
                                'Tour': tour_name,
                                'Venue': venue_name,
                                'City': city,
                                'Order': song_count,
                                'Song': song.get('name')
                            })
                            song_count += 1
                
                # API制限(1秒間に2リクエストまで)に配慮
                time.sleep(1.2)
                
            elif response.status_code == 404:
                break
            else:
                print(f"Error: {response.status_code}")
                break
                
        except Exception as e:
            print(f"An error occurred: {e}")
            break
            
    return all_data

# 実行
results = get_all_usg_setlists()
if results:
    df = pd.DataFrame(results)
    df.to_csv('usg_full_master.csv', index=False, encoding='utf-8-sig')
    print(f"\n完了！ {len(df)} 件のデータを 'usg_full_master.csv' に保存しました。")
