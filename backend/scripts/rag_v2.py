"""记忆外部化: deliberation.py 加入 RAG 检索"""
p = r'D:\Reasonix\Reasonixworkspace\novel-world-engine\backend\app\engine\deliberation.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Add RAG retriever function after imports
c = c.replace(
    'from app.llm.client import LLMClient',
    'from app.llm.client import LLMClient\n\n\ndef _rag_memories(char_id: str, query: str) -> str:\n    try:\n        from app.memory.external_memory import RAGRetriever\n        rag = RAGRetriever()\n        results = rag.search(char_id, query[:200], top_k=3)\n        if results:\n            items = [f"  - {r[1][:100]}" for r in results]\n            return "\\\\n".join(items)\n    except Exception:\n        pass\n    return ""'
)

# 2. In make_decision, add RAG memories to prompt
old_end_of_list = "    if constraints:\n        char_prompt_parts.append(f\"\\n【约束】\\n\" + \"\\n\".join(f\"- {c}\" for c in constraints))\n\n    full_prompt = \"\\n\".join(char_prompt_parts)"
new_end_of_list = "    if constraints:\n        char_prompt_parts.append(f\"\\n【约束】\\n\" + \"\\n\".join(f\"- {c}\" for c in constraints))\n    rm = _rag_memories(char.id, perception_text)\n    if rm:\n        char_prompt_parts.append(f\"\\n【相关记忆】\\n{rm}\")\n\n    full_prompt = \"\\n\".join(char_prompt_parts)"

c = c.replace(old_end_of_list, new_end_of_list)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

import py_compile
try: py_compile.compile(p, doraise=True); print('OK')
except py_compile.PyCompileError as e: print(f'Error: {e}')
