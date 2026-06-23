import pandas as pd

# 1. データ読み込みと欠損値の削除
df = pd.read_csv('usg_full_master.csv')
df = df.dropna(subset=['Song'])

# データのソート（時系列・演奏順）
df = df.sort_values(by=['Date', 'Venue', 'Order'])

# 分母のカウント
total_lives = len(df.groupby(['Date', 'Venue']))
# 「No Tour Data(フェス等)」を除いた純粋なワンマンツアーの総数をカウント
tour_df = df[df['Tour'] != 'No Tour Data']
total_tours = tour_df['Tour'].nunique()

print(f"分析を開始します（総公演数: {total_lives} / 総ツアー数: {total_tours}）...\n")

# 各曲が「何個のツアーで演奏されたか」をカウント
song_tour_counts = tour_df.groupby('Song')['Tour'].nunique().to_dict()

# ==========================================
# 集計用辞書の初期化
# ==========================================
pair_lives_count = {}  # ペアごとの演奏公演数
pair_tours_set = {}    # ペアごとの演奏ツアー（重複排除用）

next_lives_count = {}  # 直後繋ぎの演奏公演数
next_tours_set = {}    # 直後繋ぎの演奏ツアー（重複排除用）

# (1) 公演単位 ＆ ツアー単位のペア・繋ぎ集計
for (date, venue), group in df.groupby(['Date', 'Venue']):
    songs = group['Song'].tolist()
    tour = group['Tour'].iloc[0]
    is_real_tour = (tour != 'No Tour Data')
    
    # 同一ライブ内の全組み合わせ
    unique_songs = list(set(songs))
    for i in range(len(unique_songs)):
        for j in range(i + 1, len(unique_songs)):
            s1, s2 = unique_songs[i], unique_songs[j]
            pair = tuple(sorted([s1, s2]))
            
            pair_lives_count[pair] = pair_lives_count.get(pair, 0) + 1
            if is_real_tour:
                if pair not in pair_tours_set: pair_tours_set[pair] = set()
                pair_tours_set[pair].add(tour)
                
    # 直後の繋ぎ（連番）
    for k in range(len(songs) - 1):
        s1, s2 = songs[k], songs[k+1]
        flow = (s1, s2)
        
        next_lives_count[flow] = next_lives_count.get(flow, 0) + 1
        if is_real_tour:
            if flow not in next_tours_set: next_tours_set[flow] = set()
            next_tours_set[flow].add(tour)

# ==========================================
# 出力データの作成
# ==========================================
# ① 同一ライブ内ペア（Python 3.6 用に修正）
pair_results = []
for (s1, s2), l_count in pair_lives_count.items():
    t_count = len(pair_tours_set.get((s1, s2), set()))
    pair_results.append({
        '曲A': s1, '曲B': s2,
        '演奏公演数': l_count, '全公演割合': l_count / total_lives,
        '演奏ツアー数': t_count, '全ツアー割合': t_count / total_tours if total_tours > 0 else 0
    })
pair_out = pd.DataFrame(pair_results).sort_values('全ツアー割合', ascending=False)
pair_out.to_csv('usg_analysis_pair_summary.csv', index=False, encoding='utf-8-sig')

# ② 直後の繋ぎ
next_results = []
for (s1, s2), l_count in next_lives_count.items():
    t_count = len(next_tours_set.get((s1, s2), set()))
    next_results.append({
        '曲A(前)': s1, '曲B(後)': s2,
        '繋ぎ公演数': l_count, '全公演での発生割合': l_count / total_lives,
        '繋ぎツアー数': t_count, '全ツアーでの発生割合': t_count / total_tours if total_tours > 0 else 0
    })
next_out = pd.DataFrame(next_results).sort_values('全ツアーでの発生割合', ascending=False)
next_out.to_csv('usg_analysis_flow_summary.csv', index=False, encoding='utf-8-sig')

# ==========================================
# 分析③: 演奏回数が少ない上位10曲 (レア曲)
# ==========================================
rare_songs = df['Song'].value_counts().reset_index()
rare_songs.columns = ['曲名', '総演奏回数']
rare_songs = rare_songs.sort_values('総演奏回数', ascending=True).head(10)
# ==========================================
# 結果の画面出力
# ==========================================
print("【分析①：全ツアー中、共演割合が高いペア TOP 3】")
for idx, row in pair_out.head(3).iterrows():
    print(f" ペア: {row['曲A']} × {row['曲B']}")
    print(f"  └─ 演奏ツアー数: {row['演奏ツアー数']}ツアー (全ツアーの {row['全ツアー割合']:.2%})")
    print(f"  └─ (参考) 公演数: {row['演奏公演数']}公演 (全公演の {row['全公演割合']:.2%})\n")

print("【分析②：ツアーの枠を超えて愛される『直後の繋ぎ』 TOP 3】")
for idx, row in next_out.head(3).iterrows():
    print(f" 流れ: {row['曲A(前)']} ──> {row['曲B(後)']}")
    print(f"  └─ 採用ツアー数: {row['繋ぎツアー数']}ツアー (全ツアーの {row['全ツアーでの発生割合']:.2%})")
    print(f"  └─ (参考) 繋ぎ回数: {row['繋ぎ公演数']}回\n")

print("--------------------------------------------------")
print("【分析③：20年間で演奏回数が少なかった激レア曲 TOP 10】")
for idx, row in rare_songs.iterrows():
    print(f" 演奏数 {row['総演奏回数']}回 : {row['曲名']}")
