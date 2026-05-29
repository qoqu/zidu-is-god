"""长篇测试 v0.6.0 — deepseek-v4-pro"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.core import simulate

WORLD = """光明大陆西幻世界。地点: 圣光城, 暗影沼泽, 龙脊山脉, 银月森林, 铁炉堡, 风暴海, 冰霜北境。
势力: 光明教廷, 暗影议会, 龙族议会, 精灵王国, 矮人铁炉堡, 自由贸易同盟。
魔法: 元素/神圣/暗影/古代龙语。等级: 见习→初级→中级→高级→大法师→贤者→传说。
局势: 龙族有苏醒迹象, 教廷秘密行动频繁, 暗影议会在寻找龙族遗物。"""

CHARS = [
    "亚瑟, 18岁, 见习骑士, 父母在龙脊山脉失踪, 暗中调查教廷",
    "莫甘娜, 神秘女法师, 黑发紫瞳, 掌握古代龙语魔法, 寻找龙族遗物",
    "雷克斯, 35岁, 暗影议会刺客, 曾是教廷圣殿骑士后叛逃",
]

print("="*60)
print("Novel World Engine v0.6.0 — 性能测试")
print("模型: deepseek-v4-pro | fast_mode + 迷雾 + 角色分级")
print(f"章节: 5 | Beat: 3 | 角色: {len(CHARS)}")
start = time.time()

result = simulate(WORLD, CHARS, chapters=5, beats_per_chapter=3, fast_mode=True)

elapsed = time.time() - start
print(f"\n耗时: {elapsed:.0f}s ({elapsed/60:.1f}分钟)")
print(f"总字数: {result['total_words']}")
for ch in result["chapters"]:
    m = "✅" if ch["quality_passed"] else "❌"
    print(f"  第{ch['number']}章: {ch['word_count']}字 | {ch['quality']}/80 {m}")

# 追加更多章节
if len(result['chapters']) < 15:
    print(f"\n追加 5 章...")
    r2 = simulate(WORLD, CHARS, chapters=5, beats_per_chapter=3, fast_mode=True)
    elapsed2 = time.time() - start
    total = result['total_words'] + r2['total_words']
    for ch in r2["chapters"]:
        m = "✅" if ch["quality_passed"] else "❌"
        print(f"  第{ch['number']}章: {ch['word_count']}字 | {ch['quality']}/80 {m}")
    print(f"\n累计: {elapsed2/60:.1f}分钟 | {total}字")

print(f"\n✅ 测试完成")
