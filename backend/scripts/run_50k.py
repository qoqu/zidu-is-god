"""长篇测试 — deepseek-v4-flash"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.core import simulate

WORLD = """光明大陆西幻世界。地点: 圣光城, 暗影沼泽, 龙脊山脉, 银月森林, 铁炉堡, 风暴海, 冰霜北境。
势力: 光明教廷, 暗影议会, 龙族议会, 精灵王国, 矮人铁炉堡, 自由贸易同盟。
魔法: 元素/神圣/暗影/古代龙语。等级: 见习→初级→中级→高级→大法师→贤者→传说。
局势: 龙族有苏醒迹象, 教廷秘密行动频繁, 暗影议会在寻找龙族遗物, 精灵关闭边境三年。"""

CHARS = [
    "亚瑟, 18岁, 见习骑士, 父母在龙脊山脉失踪, 暗中调查教廷",
    "莫甘娜, 神秘女法师, 黑发紫瞳, 掌握古代龙语魔法, 寻找龙族遗物",
    "雷克斯, 35岁, 暗影议会刺客, 曾是教廷圣殿骑士后叛逃",
    "艾琳娜, 28岁, 精灵游侠, 奉命调查教廷异动",
    "铁锤, 120岁, 矮人锻造大师, 来圣光城交货",
]

print("="*60)
print("Novel World Engine — 长篇测试")
print(f"模型: flash | 角色: {len(CHARS)} | 章节: 8 | Beat: 4")
start=time.time()
result=simulate(WORLD, CHARS, chapters=8, beats_per_chapter=4)
elapsed=time.time()-start
print(f"\n耗时: {elapsed/60:.1f}分钟 | 总字数: {result['total_words']}")
for ch in result["chapters"]:
    m="✅" if ch["quality_passed"] else "❌"
    print(f"  第{ch['number']}章: {ch['word_count']}字 | {ch['quality']}/80 {m}")

p=os.path.join(os.path.dirname(__file__),'..','output_50k.txt')
with open(p,'w',encoding='utf-8') as f:
    for ch in result["chapters"]:
        f.write(f"\n第{ch['number']}章({ch['word_count']}字,{ch['quality']}/80)\n\n{ch['text']}\n")
print(f"\n📄 output_50k.txt ({result['total_words']}字)")
