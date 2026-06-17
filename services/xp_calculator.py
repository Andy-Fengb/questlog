"""
動態任務經驗值計算模組（保底 + 溢出模式）

支援所有彈性任務（閱讀、游泳等耗時不固定的任務）。
參數可在 config.py 中按任務覆寫。
"""

def calculate_quest_xp(
    actual_minutes: int,
    base_minutes: int = 15,
    base_xp: int = 10,
    bonus_interval: int = 5,
    bonus_xp: int = 2
) -> dict:
    """
    計算動態任務經驗值 (保底 + 溢出模式)

    Args:
        actual_minutes: 實際花費分鐘數
        base_minutes:   保底時間線（預設 15 分鐘）
        base_xp:        保底經驗值（預設 10 XP）
        bonus_interval: 溢出計算區間（每多做 N 分鐘）
        bonus_xp:       溢出區間獎勵（給 N XP）

    Returns:
        {
            'total_xp': 總經驗值,
            'base_xp':  基礎經驗值（含不足保底時的折算）,
            'bonus_xp': 溢出獎勵經驗值
        }
    """
    # 1. 連保底都沒達到 → 按比例折算，絕不讓努力白費
    if actual_minutes < base_minutes:
        earned_base = max(1, int(actual_minutes * base_xp // base_minutes))
        return {
            'total_xp': earned_base,
            'base_xp': earned_base,
            'bonus_xp': 0
        }

    # 2. 達到保底，全額基礎獎勵
    earned_base = base_xp

    # 3. 計算溢出時間
    overkill = actual_minutes - base_minutes

    # 4. 溢出獎勵（做滿完整區間才給）
    bonus_ticks = overkill // bonus_interval
    earned_bonus = bonus_ticks * bonus_xp

    return {
        'total_xp': earned_base + earned_bonus,
        'base_xp': earned_base,
        'bonus_xp': earned_bonus
    }


# ── 自測（僅直接執行時觸發） ──
if __name__ == '__main__':
    tests = [
        (10, '不足保底'),
        (15, '剛好保底'),
        (20, '保底+1個區間'),
        (25, '保底+2個區間'),
        (45, '保底+6個區間'),
        (0,  '零分鐘'),
    ]
    for mins, label in tests:
        r = calculate_quest_xp(mins)
        print(f"{label:10s} | {mins:3d}分鐘 → base={r['base_xp']:2d} bonus={r['bonus_xp']:2d} total={r['total_xp']:2d}")