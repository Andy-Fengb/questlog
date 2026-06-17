"""Quest Log v2 — Configuration & Constants."""
import os, datetime

DB_PATH = '/app/questlog.db'

# ── Levels ──
LEVELS = []
total = 0
for lv in range(1, 21):
    need = 100 + (lv - 1) * 50 if lv > 1 else 0
    total += need
    LEVELS.append({'level': lv, 'xp_needed': need, 'xp_cumulative': total})

def get_level(xp):
    for l in reversed(LEVELS):
        if xp >= l['xp_cumulative']:
            return l
    return LEVELS[0]

def today():
    return datetime.date.today().isoformat()

# ── Motivational Tips ──
TIPS = [
    '只有将大目标拆解为具体的行动步骤，才能获得稳定的掌控感。',
    '不要等待完美的时机，现在就是最好的开始。',
    '每天进步 1%，一年后你就是原来的 37 倍。',
    '完成比完美更重要。',
    '习惯的力量在于重复，而非强度。',
    '你不需要看到整条路，只需迈出下一步。',
    '今天的努力，是明天的底气。',
]

import random
def get_tip():
    return random.choice(TIPS)

# ── CN Achievements (preserved from v1) ──
CN_ACHIEVEMENTS = [
    {'id': 'cn_education', 'cat': '新手村', 'name': '🎒 九年义务防沉迷',
     'desc': '熬過基礎教程階段，解鎖初級心智模型和基礎算力。', 'rarity': 'common',
     'trigger': 'level', 'value': 10, 'xp_reward': 10},
    {'id': 'cn_gaokao', 'cat': '新手村', 'name': '🎒 五年高考，三年模拟',
     'desc': '國服第一深淵副本。歷經無數次「模擬考」耐久度測試，獲得【大學錄取通知書】通行證。', 'rarity': 'uncommon',
     'trigger': 'level', 'value': 18, 'xp_reward': 30},
    {'id': 'cn_cet', 'cat': '新手村', 'name': '🎒 英语四六级守门员',
     'desc': '全服強制語言模塊補丁測試，無數玩家在此卡關多年。', 'rarity': 'uncommon',
     'trigger': 'task_count_any', 'tasks': ['ielts_listen','ielts_read'], 'value': 50, 'xp_reward': 50},
    {'id': 'cn_kaobian', 'cat': '轉職', 'name': '💼 宇宙的尽头是考编',
     'desc': '參與「千軍萬馬過獨木橋」吃雞模式。獲得史詩級綁定防具【鐵飯碗】抗風險能力 +999%。', 'rarity': 'epic',
     'trigger': 'level', 'value': 30, 'xp_reward': 100},
    {'id': 'cn_worker', 'cat': '轉職', 'name': '💼 天命早八人',
     'desc': '加入企業公會。獲得成就專屬技能「地鐵/公車跑酷大師」。', 'rarity': 'common',
     'trigger': 'streak', 'value': 7, 'xp_reward': 20},
    {'id': 'cn_996', 'cat': '轉職', 'name': '💼 赛博修仙者',
     'desc': '體驗 996 福報特殊結界。發量上限永久減少，頸椎/腰椎耐久度加速掉血。', 'rarity': 'epic',
     'trigger': 'streak', 'value': 30, 'xp_reward': 100},
    {'id': 'cn_house', 'cat': '終局', 'name': '🏠 三十年卖身契',
     'desc': '獲得專屬避難所（房產證）。被施加長達 20-30 年的「房貸封印」每月自動扣金幣。', 'rarity': 'legendary',
     'trigger': 'level', 'value': 50, 'xp_reward': 200},
    {'id': 'cn_dating', 'cat': '終局', 'name': '🏠 高端相亲局',
     'desc': 'PVP+PVE 社交盲盒。需比拼雙方面板屬性（學歷、家境、金幣數量），極度消耗 SAN 值。', 'rarity': 'epic',
     'trigger': 'task_sum', 'task_id': 'ccnp', 'value': 500, 'xp_reward': 100},
    {'id': 'cn_kid', 'cat': '終局', 'name': '🏠 四脚吞金兽',
     'desc': '解鎖隱藏傳承系統。成功孵化下一代帳號後，金幣消耗速率永久提升 300%，且無法卸載。', 'rarity': 'legendary',
     'trigger': 'total_tasks', 'value': 365, 'xp_reward': 200},
    {'id': 'cn_chunyun', 'cat': '活動', 'name': '🎉 地表最大迁徙',
     'desc': '在一年一度的「春運」限時活動中，搶到一張回城卷軸（車票）。', 'rarity': 'event',
     'trigger': 'spring_festival', 'xp_reward': 50},
    {'id': 'cn_pinduoduo', 'cat': '活動', 'name': '🎉 帮我砍一刀',
     'desc': '觸發拼刀刀社交裂變魔法。極度考驗好友數量與臉皮厚度。', 'rarity': 'mythic',
     'trigger': 'never', 'value': 0, 'xp_reward': 0},
    {'id': 'cn_singles', 'cat': '活動', 'name': '🎉 双十一尾款人',
     'desc': '在全服大型電商狂歡節中，熬夜釋放購買技能，體驗金幣瞬間清零的大魔法。', 'rarity': 'event',
     'trigger': 'date_check', 'month': 11, 'day': 11, 'xp_reward': 50},
    {'id': 'cn_gossip', 'cat': '活動', 'name': '🎉 一线吃瓜群众',
     'desc': '在微博、抖音等信息流地圖中，見證某位 NPC（明星/網紅）人設崩塌的史詩級劇情。', 'rarity': 'event',
     'trigger': 'all_done_30', 'value': 30, 'xp_reward': 50},
]
