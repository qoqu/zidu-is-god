"""记忆外部化: 决策 prompt 用 RAG 检索"""
p = r'D:\Reasonix\Reasonixworkspace\novel-world-engine\backend\app\engine\deliberation.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

old_start = "    char_prompt_parts = ["
new_start = '''    rag_memories = ""
    try:
        from app.memory.external_memory import RAGRetriever
        rag = RAGRetriever()
        results = rag.search(char.id, perception_text[:200], top_k=3)
        if results:
            rag_memories = "\\n".join(f"  - {r[1][:100]}" for r in results)
    except Exception:
        pass
    
    char_prompt_parts = ['''

c = c.replace(old_start, new_start)

# Find where the char_prompt_parts list ends and append RAG
old_end_list = '    if constraints:\n        char_prompt_parts.append(f\"\\n【约束】\\n\" + \"\\n\".join(f\"- {c}\" for c in constraints))'
new_end_list = '''    if constraints:
        char_prompt_parts.append(f\"\\n【约束】\\n\" + \"\\n\".join(f\"- {c}\" for c in constraints))
    if rag_memories:
        char_prompt_parts.append(f\"\\n【相关记忆】\\n{rag_memories}\")'''

c = c.replace(old_end_list, new_end_list)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

import py_compile
try:
    py_compile.compile(p, doraise=True)
    print('OK')
except py_compile.PyCompileError as e:
    print(f'Error at line {e.lineno}: {e.msg}')
