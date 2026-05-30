"""
Novel World Engine — 50章长篇测试
在你自己电脑上双击运行, 没有超时限制
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.core import simulate

WORLD = open(os.path.join(os.path.dirname(__file__), '..', 'examples', '西幻_光明大陆_世界观.txt'), encoding='utf-8').read()
CHARS = [l.strip() for l in open(os.path.join(os.path.dirname(__file__), '..', 'examples', '西幻_光明大陆_角色.txt'), encoding='utf-8') if l.strip()]

TOTAL_CHAPTERS = 5
BEATS = 3

print("=" * 60)
print(f"Novel World Engine — {TOTAL_CHAPTERS}章长篇测试")
print(f"模型: deepseek-v4-pro | fast_mode=True")
print(f"角色: 3 | 每章 {BEATS} Beat")
print("=" * 60)
print()
progress = {"current": 0, "total": TOTAL_CHAPTERS}

def cb(stage, cur, total, msg):
    progress["current"] = cur
    progress["total"] = total
    if stage in ("running", "building_world", "generating_chars"):
        print(f"  [{cur}/{total}] {msg}")
        sys.stdout.flush()

print("  [0/50] 正在构建世界... (可能需要30-60秒)")
sys.stdout.flush()
start = time.time()
result = simulate(WORLD, CHARS, chapters=TOTAL_CHAPTERS, beats_per_chapter=BEATS, fast_mode=True, progress_callback=cb)
elapsed = time.time() - start

print(f"\n{'='*60}")
print(f"✅ 完成!")
print(f"   耗时: {elapsed/60:.1f} 分钟")
print(f"   总字数: {result['total_words']}")
print(f"   平均质量: {sum(result['quality_scores'])/len(result['quality_scores']):.0f}/80")
print(f"{'='*60}\n")

for c in result['chapters']:
    m = "✅" if c['quality_passed'] else "❌"
    print(f"  第{c['number']}章: {c['word_count']}字 | {c['quality']}/80 {m}")

out = os.path.join(os.path.dirname(__file__), '..', f'output_{TOTAL_CHAPTERS}ch.txt')
with open(out, 'w', encoding='utf-8') as f:
    f.write(f"Novel World Engine — {TOTAL_CHAPTERS}章 | {result['total_words']}字 | {elapsed/60:.1f}分钟\n\n")
    for c in result['chapters']:
        f.write(f"\n第{c['number']}章 ({c['word_count']}字 | {c['quality']}/80)\n{'='*40}\n{c['text']}\n")

print(f"\n📄 已保存: {out}")
input("\n按 Enter 键退出...")
