"""重构 WorldBuilder — 惰性初始化 + 按需展开"""
p = r'D:\Reasonix\Reasonixworkspace\novel-world-engine\backend\app\world\builder.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# Keep ACTION_GEN_PROMPT, WEATHER_GEN_PROMPT but remove THREAT_GEN and EVENT_GEN from module level
# Add new lazy methods to WorldBuilder

# Add lazy expansion prompts before class
c = c.replace(
    'class WorldBuilder:',
    '''EXPAND_LOCATION_PROMPT = """根据世界观和当前故事进度, 生成一个新地点。
当前世界: {world_name} {world_desc}
角色从 {from_location} 向 {direction} 探索。
当前故事进展到第 {chapter} 章。

返回 JSON:
{
  "id": "loc_{id}",
  "name": "地点名",
  "description": "描述(含特色、危险程度、关键NPC)",
  "nearby": ["相邻地点id"],
  "importance": 1-5,
  "type": "city/forest/dungeon/temple/wilderness/...",
  "factions_present": ["关联势力id"]
}
只返回 JSON。"""

GENERATE_THREAT_PROMPT = """当前故事进入高潮, 需要设计一个威胁。当前故事进展到第{chapter}章, 当前张力{tension}。
世界观: {world_desc}
已有角色: {chars}
已有威胁: {existing_threats}

返回 JSON:
{
  "name": "威胁名",
  "description": "威胁描述",
  "natural_growth": 0.001-0.01,
  "trigger_threshold": 0.8-1.0,
  "accelerates_by": ["加速的影响力维度"],
  "decelerates_by": ["减缓的影响力维度"],
  "effects": {"danger_level": "+数字"}
}
只返回 JSON。"""

GENERATE_EVENT_PROMPT = """根据当前世界状态, 生成一个随机事件。第{chapter}章, 地点{location}。
世界观: {world_desc}

返回 JSON:
{
  "type": "disaster/opportunity/faction/celebration",
  "title": "事件标题",
  "desc": "事件描述(用{location}代替地点名)",
  "severity": 1-5,
  "duration_days": 1-10,
  "effects": {}
}
只返回 JSON。"""

class WorldBuilder:"""

c = c.replace(old, new)

# Now update the build method and add lazy methods
# Replace build_actions, build_weather, build_threats, build_events, build_extras, build
old_methods_block_start = c.find('    def build_actions(self, world_description: str) -> list:')
old_methods_block_end = c.find('\n    def build(self, world_description: str) -> World:\n')
if old_methods_block_start >= 0 and old_methods_block_end > old_methods_block_start:
    before = c[:old_methods_block_start]
    after = c[old_methods_block_end:]
    
    new_methods = '''    def build_initial(self, world_description: str) -> World:
        """只生成初始地点 + 周边 —— 不生成威胁/事件/Actor"""
        try:
            data = self.llm.chat_json(system_prompt=WORLD_BUILD_SYSTEM_PROMPT, user_prompt=world_description[:3000])
        except Exception:
            data = {}
        world = World(id="world", name=data.get("name", "未知世界"),
                      description=data.get("description", world_description[:200]))
        for loc in data.get("locations", [])[:3]:  # 只取前3个
            lid = loc.get("id", f"loc_{len(world.locations)}")
            world.locations[lid] = Location(id=lid, name=loc.get("name", ""), description=loc.get("description", ""))
        for fac in data.get("factions", [])[:2]:  # 只取前2个
            fid = fac.get("id", f"fac_{len(world.factions)}")
            world.factions[fid] = Faction(id=fid, name=fac.get("name", ""), description=fac.get("description", ""))
        for rule in data.get("rules", [])[:3]:
            world.rules.append(WorldRule(name=rule.get("name", ""), description=rule.get("description", ""), category=rule.get("category", "general")))
        world.extras = {"actions": [], "weather": [], "threats": [], "events": []}
        return world

    def expand_location(self, world, from_location_id: str, direction: str = "前方", chapter: int = 1) -> str:
        """角色探索到新区域时, 按需生成新地点"""
        from_loc = world.locations.get(from_location_id)
        from_name = from_loc.name if from_loc else from_location_id
        prompt = EXPAND_LOCATION_PROMPT.format(
            world_name=world.name, world_desc=world.description[:300],
            from_location=from_name, direction=direction, chapter=chapter,
        )
        try:
            data = self.llm.chat_json("生成新地点", f"{prompt}\\n\\nid前缀: loc_{len(world.locations)+1}")
            if data and data.get("name"):
                lid = data.get("id", f"loc_{len(world.locations)+1}")
                world.locations[lid] = Location(id=lid, name=data["name"], description=data.get("description", ""))
                return lid
        except Exception:
            pass
        return ""

    def generate_threat(self, world, chapter: int, tension: float = 0.5, chars: list = None) -> dict:
        """张力达到阈值时按需生成威胁"""
        existing = list(world.extras.get("threats", []))
        prompt = GENERATE_THREAT_PROMPT.format(
            chapter=chapter, tension=tension, world_desc=world.description[:300],
            chars=", ".join(c.name for c in (chars or []))[:200],
            existing_threats=", ".join(t.get("name","") for t in existing)[:200],
        )
        try:
            data = self.llm.chat_json("生成威胁", prompt)
            if data and data.get("name"):
                threats = world.extras.setdefault("threats", [])
                threats.append(data)
                return data
        except Exception:
            pass
        return {}

    def generate_event(self, world, chapter: int, location_id: str = "") -> dict:
        """按需生成随机事件"""
        loc_name = world.locations.get(location_id, Location(id="", name="未知")).name if location_id else "未知"
        prompt = GENERATE_EVENT_PROMPT.format(chapter=chapter, location=loc_name, world_desc=world.description[:300])
        try:
            data = self.llm.chat_json("生成事件", prompt)
            if data and data.get("title"):
                events = world.extras.setdefault("events", [])
                events.append(data)
                return data
        except Exception:
            pass
        return {}

    def build_actions(self, world_description: str) -> list:
        try:
            d = self.llm.chat_json(ACTION_GEN_PROMPT, world_description[:2000])
            return d if isinstance(d, list) else []
        except: return []

    def build_weather(self, world_description: str) -> list:
        try:
            d = self.llm.chat_json(WEATHER_GEN_PROMPT, world_description[:2000])
            return d if isinstance(d, list) else []
        except: return []

    def build(self, world_description: str) -> World:
        return self.build_initial(world_description)
'''
    
    c = before + new_methods + after

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

import py_compile
try:
    py_compile.compile(p, doraise=True)
    print('OK')
except py_compile.PyCompileError as e:
    print(f'Error at line {e.lineno}: {e.msg}')
