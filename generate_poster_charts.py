import os
import itertools
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# 日本語フォントの設定（環境に合わせて自動適用）
plt.rcParams['font.family'] = 'MS Gothic'
sns.set(font="MS Gothic")

desktop_path = os.path.join(os.path.expanduser('~'), 'OneDrive', 'デスクトップ')
if not os.path.exists(desktop_path):
    desktop_path = '.'

print("=== ポスター発表用データ分析スクリプト（全手法・実データ版）を開始します ===")

# ==========================================
# 1. CSVデータの読み込みと前処理
# ==========================================
path_master = os.path.join(desktop_path, 'usg_full_master_japanese.csv')
path_yt = os.path.join(desktop_path, 'usg_youtube_stats.csv')

if not os.path.exists(path_master) and os.path.exists('usg_full_master_japanese.csv'):
    path_master = 'usg_full_master_japanese.csv'
if not os.path.exists(path_yt) and os.path.exists('usg_youtube_stats.csv'):
    path_yt = 'usg_youtube_stats.csv'

df_master = pd.read_csv(path_master)
df_yt = pd.read_csv(path_yt) if os.path.exists(path_yt) else pd.DataFrame()

# 演奏回数のカウント
play_counts = df_master['Song'].value_counts().reset_index()
play_counts.columns = ['Song', 'Live_Play_Count']

# YouTubeデータとの結合
df_merged = df_yt.merge(play_counts, on='Song', how='left') if not df_yt.empty else play_counts
df_merged['Live_Play_Count'] = df_merged['Live_Play_Count'].fillna(0).astype(int)
df_merged['MV_View_Count'] = pd.to_numeric(df_merged.get('MV_View_Count', 0), errors='coerce').fillna(0)


# ==========================================
# 【手法1】 アソシエーション分析（ツアー単位のセットリスト併発ルール）
# ==========================================
print("\n[手法1] ツアー単位でのアソシエーション分析を実行中...")

df_tours = df_master[df_master['Tour'] != 'No Tour Data']
basket_tour = (pd.crosstab(df_tours['Tour'], df_tours['Song']) > 0).astype(int)

total_tours = len(basket_tour)
tour_supports = basket_tour.mean(axis=0)

# 85%以上の超・定番曲を除外し、ツアー固有の併発関係を抽出
varied_songs = [s for s in basket_tour.columns if 0.10 <= tour_supports[s] <= 0.85]

rules_tour = []
for s1, s2 in itertools.permutations(varied_songs, 2):
    sup_s1 = tour_supports[s1]
    sup_s2 = tour_supports[s2]
    sup_both = (basket_tour[s1] & basket_tour[s2]).mean()
    
    if (sup_both * total_tours) >= 3 and sup_s1 > 0 and sup_s2 > 0:
        conf = sup_both / sup_s1
        lift = conf / sup_s2
        rules_tour.append({
            'Rule': f"{s1}  →  {s2}",
            'Support': sup_both,
            'Confidence': conf,
            'Lift': lift
        })

df_assoc = pd.DataFrame(rules_tour).sort_values('Lift', ascending=False)
df_assoc_top = df_assoc.drop_duplicates(subset=['Lift']).head(10)

plt.figure(figsize=(10.5, 5.5))
bars = plt.barh(df_assoc_top['Rule'], df_assoc_top['Lift'], color='#2ecc71')

for bar, conf_val in zip(bars, df_assoc_top['Confidence']):
    width = bar.get_width()
    plt.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
             f'Lift: {width:.2f} (併発率: {conf_val:.1%})', 
             va='center', ha='left', fontsize=9)

plt.axvline(x=1.0, color='red', linestyle='--', label='基準線 (Lift=1.0: 偶然レベル)')
plt.title('手法1: アソシエーション分析（ツアー単位のセトリ連動ルール Top10）', fontsize=12, fontweight='bold')
plt.xlabel('リフト値 (Lift: 単なる偶然を超えて同じツアーセトリに入った倍率)', fontsize=10)
plt.xlim(0, max(df_assoc_top['Lift']) + 2.5)
plt.gca().invert_yaxis()
plt.legend(loc='lower right')
plt.grid(True, ls='--', alpha=0.5)

save_chart1 = os.path.join(desktop_path, 'poster_fig1_association.png')
plt.savefig(save_chart1, dpi=300, bbox_inches='tight')
plt.close()
print(f" └ 図1保存完了: {save_chart1}")


# ==========================================
# 【手法2】 Jaccard共起 ＆ ネットワーク分析（主要楽曲相関マップ）
# ==========================================
print("\n[手法2] ネットワーク分析（セトリ共起関係）を作成中...")

live_basket = (pd.crosstab(df_master['Date'], df_master['Song']) > 0).astype(int)
cooccurrence_matrix = live_basket.T.dot(live_basket)

G = nx.Graph()
top_25_songs = df_master['Song'].value_counts().head(25).index.tolist()

for s in top_25_songs:
    play_cnt = df_master[df_master['Song'] == s].shape[0]
    G.add_node(s, size=play_cnt)

for s1, s2 in itertools.combinations(top_25_songs, 2):
    if s1 in cooccurrence_matrix.index and s2 in cooccurrence_matrix.columns:
        w = cooccurrence_matrix.loc[s1, s2]
        if w >= 10:
            G.add_edge(s1, s2, weight=w)

plt.figure(figsize=(11, 8.5))
pos = nx.spring_layout(G, k=0.6, seed=42)
node_sizes = [G.nodes[n].get('size', 10) * 1.5 for n in G.nodes()]

nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='#e74c3c', alpha=0.85)
nx.draw_networkx_edges(G, pos, width=[G[u][v]['weight']*0.08 for u,v in G.edges()], alpha=0.35, edge_color='gray')
nx.draw_networkx_labels(G, pos, font_family='MS Gothic', font_size=8.5, font_weight='bold')

plt.title('手法2: ライブセトリ共起ネットワーク（主要25曲の共演関係）', fontsize=12, fontweight='bold')
plt.axis('off')

save_chart2 = os.path.join(desktop_path, 'poster_fig2_network.png')
plt.savefig(save_chart2, dpi=300, bbox_inches='tight')
plt.close()
print(f" └ 図2保存完了: {save_chart2}")


# ==========================================
# 【手法3】 k-meansクラスタリング（楽曲の役割分類）
# ==========================================
print("\n[手法3] k-meansクラスタリング（楽曲分類）を実行中...")

df_merged['Log_MV_View'] = np.log10(df_merged['MV_View_Count'].replace(0, 1))

X_cluster = df_merged[['Log_MV_View', 'Live_Play_Count']].fillna(0)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_cluster)

kmeans = KMeans(n_clusters=4, random_state=42)
df_merged['Cluster'] = kmeans.fit_predict(X_scaled)

cluster_summary = df_merged.groupby('Cluster').agg({
    'Log_MV_View': 'mean',
    'Live_Play_Count': 'mean'
}).reset_index()

c_sorted = cluster_summary.sort_values(by=['Live_Play_Count', 'Log_MV_View'], ascending=False).reset_index(drop=True)
c_map = {
    c_sorted.loc[0, 'Cluster']: '代表キラーチューン',
    c_sorted.loc[1, 'Cluster']: 'ライブ常連定番曲',
    c_sorted.loc[2, 'Cluster']: 'MV人気・特定曲',
    c_sorted.loc[3, 'Cluster']: 'アルバム・レア曲'
}
df_merged['Cluster_Name'] = df_merged['Cluster'].map(c_map)

palette_dict = {
    '代表キラーチューン': '#e74c3c',
    'ライブ常連定番曲': '#3498db',
    'MV人気・特定曲': '#e67e22',
    'アルバム・レア曲': '#2ecc71'
}

plt.figure(figsize=(10, 6))
sns.scatterplot(
    data=df_merged, 
    x='MV_View_Count', 
    y='Live_Play_Count', 
    hue='Cluster_Name', 
    style='Cluster_Name',
    palette=palette_dict, 
    s=120
)

key_songs = ['シュガーソングとビターステップ', 'オリオンをなぞる', '天国と地獄', 'カオスが極まる', '君の瞳に恋してない', '桜のあと (all quartets lead to the?)', '傍若のカリスマ', 'fake town baby']
for _, row in df_merged[df_merged['Song'].isin(key_songs)].iterrows():
    plt.text(row['MV_View_Count']*1.08, row['Live_Play_Count'], row['Song'], fontsize=8)

plt.xscale('log')
plt.title('手法3: k-meansクラスタリングによる楽曲の役割分類', fontsize=12, fontweight='bold')
plt.xlabel('YouTube MV再生回数（対数スケール）', fontsize=10)
plt.ylabel('ライブ通算演奏回数', fontsize=10)
plt.legend(title='楽曲タイプ', loc='upper left')
plt.grid(True, ls='--', alpha=0.5)

save_chart3 = os.path.join(desktop_path, 'poster_fig3_kmeans.png')
plt.savefig(save_chart3, dpi=300, bbox_inches='tight')
plt.close()
print(f" └ 図3保存完了: {save_chart3}")


# ==========================================
# 【手法4】 ライブ形態（ツアー種別）ごとの楽曲タイプ構成比率
# ==========================================
print("\n[手法4] ツアー形態別の構成比率グラフを作成中...")

def categorize_tour(tour_name):
    if any(k in str(tour_name) for k in ['Program', '15th', '20th', 'BEST', 'BEST MACHINE', 'Bee-side']):
        return '周年・ベストツアー'
    elif tour_name == 'No Tour Data':
        return 'イベント・フェス等'
    else:
        return 'アルバム全国ツアー'

df_master['Tour_Category'] = df_master['Tour'].apply(categorize_tour)
df_master_clustered = df_master.merge(df_merged[['Song', 'Cluster_Name']], on='Song', how='left')
df_master_clustered['Cluster_Name'] = df_master_clustered['Cluster_Name'].fillna('アルバム・レア曲')

tour_comp = pd.crosstab(df_master_clustered['Tour_Category'], df_master_clustered['Cluster_Name'], normalize='index') * 100
col_order = ['代表キラーチューン', 'ライブ常連定番曲', 'MV人気・特定曲', 'アルバム・レア曲']
col_order_existing = [c for c in col_order if c in tour_comp.columns]
tour_comp = tour_comp[col_order_existing]

tour_comp.plot(kind='bar', stacked=True, figsize=(9, 5.5), color=[palette_dict[c] for c in col_order_existing])
plt.title('手法4: ライブ形態（ツアー種別）ごとの楽曲タイプ構成比率', fontsize=12, fontweight='bold')
plt.xlabel('ライブの形態・タイプ', fontsize=10)
plt.ylabel('セットリスト内の楽曲割合（%）', fontsize=10)
plt.legend(title='楽曲タイプ', bbox_to_anchor=(1.02, 1), loc='upper left')
plt.xticks(rotation=0)
plt.grid(True, ls='--', alpha=0.3)

save_chart4 = os.path.join(desktop_path, 'poster_fig4_tour_composition.png')
plt.savefig(save_chart4, dpi=300, bbox_inches='tight')
plt.close()
print(f" └ 図4保存完了: {save_chart4}")

print("\n処理完了")