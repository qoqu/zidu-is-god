"""替换旧 index.html 为新 Web UI"""
p = r'D:\Reasonix\Reasonixworkspace\novel-world-engine\backend\frontend\index.html'
with open(p, 'w', encoding='utf-8') as f:
    f.write('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Novel World Engine</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d0d0d;color:#e0e0e0;font-family:'Segoe UI',sans-serif;display:flex;height:100vh}
/* 侧边栏 */
.sidebar{width:240px;background:#141414;border-right:1px solid #222;padding:16px;display:flex;flex-direction:column}
.sidebar h1{font-size:16px;color:#e0c080;margin-bottom:16px}
.sidebar .phase{font-size:13px;padding:6px 10px;margin:2px 0;border-radius:4px;cursor:pointer;color:#666}
.sidebar .phase.active{background:#2a2a2a;color:#e0c080}
.sidebar .phase.done{color:#4a4}
.sidebar .phase.current{color:#e0c080;font-weight:600}
/* 主区域 */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.header{padding:12px 20px;border-bottom:1px solid #222;font-size:13px;color:#888;display:flex;gap:12px}
.header .badge{background:#2a2a2a;padding:2px 8px;border-radius:3px;font-size:11px;color:#aaa}
/* 聊天区 */
.chat{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}
.msg{max-width:80%;padding:10px 14px;border-radius:8px;font-size:14px;line-height:1.6}
.msg.ai{background:#1a1a2a;align-self:flex-start;border:1px solid #2a2a4a}
.msg.user{background:#2a2a1a;align-self:flex-end;border:1px solid #4a4a2a}
.msg .opt{display:block;padding:6px 10px;margin:4px 0;background:#222;border-radius:4px;cursor:pointer;color:#ccc;font-size:13px}
.msg .opt:hover{background:#333;color:#e0c080}
/* 输入区 */
.input-bar{display:flex;padding:12px 20px;border-top:1px solid #222;background:#141414}
.input-bar input{flex:1;background:#1a1a1a;border:1px solid #333;border-radius:4px;padding:10px;color:#e0e0e0;font-size:14px;outline:none}
.input-bar input:focus{border-color:#e0c080}
.input-bar button{background:#e0c080;color:#111;border:none;border-radius:4px;padding:10px 20px;margin-left:8px;cursor:pointer;font-weight:600}
.input-bar button:disabled{opacity:.5;cursor:default}
/* 右侧面板 */
.panel{width:320px;border-left:1px solid #222;padding:16px;overflow-y:auto;background:#111}
.panel h3{font-size:13px;color:#e0c080;margin-bottom:8px}
.panel .item{padding:6px 8px;margin:3px 0;background:#1a1a1a;border-radius:4px;font-size:12px;color:#aaa}
.panel .item .tag{display:inline-block;background:#2a2a2a;padding:1px 6px;border-radius:2px;font-size:10px;margin-left:4px}
.tag.full{background:#2a4a2a;color:#8c8}
.tag.light{background:#4a4a2a;color:#cc8}
.tag.none{background:#4a2a2a;color:#c88}
</style>
</head>
<body>

<div class="sidebar" id="sidebar">
  <h1>✧ Novel World<br>Engine</h1>
  <div id="phaseList"></div>
</div>

<div class="main">
  <div class="header">
    <span id="sessionStatus">未开始</span>
    <span class="badge" id="worldBadge"></span>
    <span class="badge" id="sceneBadge"></span>
    <span class="badge" id="charBadge"></span>
  </div>
  <div class="chat" id="chat"></div>
  <div class="input-bar">
    <input id="input" placeholder="输入..." onkeydown="if(event.key==='Enter')send()">
    <button id="sendBtn" onclick="send()">发送</button>
  </div>
</div>

<div class="panel" id="panel">
  <h3>状态</h3>
  <div id="panelContent">
    <div style="color:#555;font-size:13px">开始交互式构建后显示</div>
  </div>
</div>

<script>
// ---- 状态 ----
let sessionId = null;
let currentStage = '';
let phases = [
  {id:'world_build', label:'世界观', done:false},
  {id:'scene_design', label:'场景设计', done:false},
  {id:'character_design', label:'角色设计', done:false},
  {id:'direction', label:'方向设定', done:false},
  {id:'run', label:'运行模拟', done:false},
  {id:'review', label:'审阅', done:false},
];

// ---- 阶段列表 ----
function renderPhases(){
  const el = document.getElementById('phaseList');
  el.innerHTML = phases.map((p,i) => 
    '<div class="phase ' + (p.done?'done':'') + (i===0?' active':'') + '">'
    + (p.done?'✅ ':'○ ') + p.label + '</div>'
  ).join('');
}
renderPhases();

// ---- 消息 ----
function addMsg(role, text){
  const chat = document.getElementById('chat');
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.innerHTML = text.replace(/\\n/g,'<br>');
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function addOptions(options){
  const chat = document.getElementById('chat');
  const div = document.createElement('div');
  div.className = 'msg ai';
  div.innerHTML = '<div class="opt" onclick="selectOption(0)">' + options.join('</div><div class="opt" onclick="selectOption(' + options.map((_,i)=>i).join(')">') + ')">' + options.join('</div>');
  // 简化: 直接生成
  div.innerHTML = options.map((o,i) => '<div class="opt" onclick="send(\'' + (i+1) + '\')">' + (i+1) + '. ' + o + '</div>').join('');
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

// ---- 交互 ----
function send(text){
  const input = document.getElementById('input');
  const btn = document.getElementById('sendBtn');
  const msg = text || input.value.trim();
  if(!msg) return;
  input.value = '';
  
  addMsg('user', msg);
  btn.disabled = true;
  
  if(!sessionId){
    // 开始新的会话
    fetch('/api/wb/start', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({stage: currentStage || 'world_build'})
    }).then(r=>r.json()).then(data => {
      sessionId = data.session_id;
      currentStage = data.stage || 'world_build';
      addMsg('ai', data.message);
      btn.disabled = false;
      updatePanel();
    }).catch(e => { addMsg('ai', '连接失败: ' + e.message); btn.disabled = false; });
    return;
  }
  
  fetch('/api/wb/input', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({session_id: sessionId, text: msg})
  }).then(r=>r.json()).then(data => {
    if(data.message) addMsg('ai', data.message);
    if(data.done){
      // 标记当前阶段完成, 进入下一阶段
      const idx = phases.findIndex(p => p.id === (currentStage || 'world_build'));
      if(idx >= 0) phases[idx].done = true;
      renderPhases();
      // 自动进入下一阶段
      const next = {world_build:'scene_design', scene_design:'character_design', character_design:'direction', direction:'run'}[currentStage];
      if(next && next !== 'run'){
        currentStage = next;
        sessionId = null; // 新阶段需要新会话
        addMsg('ai', '进入下一阶段: ' + (phases.find(p=>p.id===next)?.label || next));
      } else if(next === 'run'){
        // 自动运行
        runSimulation();
      }
    }
    updatePanel();
    btn.disabled = false;
  }).catch(e => { addMsg('ai', '错误: ' + e.message); btn.disabled = false; });
}

// ---- 运行模拟 ----
function runSimulation(){
  if(!sessionId){ addMsg('ai', '没有可运行的会话'); return; }
  addMsg('ai', '开始模拟...');
  
  fetch('/api/wb/run', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({session_id: sessionId})
  }).then(r=>r.json()).then(data => {
    if(data.error){
      addMsg('ai', '模拟失败: ' + data.error + (data.warnings ? '\\\\n' + JSON.stringify(data.warnings) : ''));
      return;
    }
    if(data.chapters){
      addMsg('ai', '✅ 完成! 共' + data.total_words + '字');
      data.chapters.forEach(ch => {
        addMsg('ai', '<b>第' + ch.number + '章</b> (' + ch.word_count + '字, ' + ch.quality + '/80)<br>' + ch.text.substring(0,200) + '...');
      });
      // 进入审阅阶段
      currentStage = 'review';
      const idx = phases.findIndex(p => p.id === 'run');
      if(idx >= 0) phases[idx].done = true;
      renderPhases();
      addMsg('ai', '可以对某一章提修改意见。例: "第3章节奏太慢了, 加快"');
    }
    updatePanel();
  }).catch(e => addMsg('ai', '错误: ' + e.message));
}

// ---- 审阅 ----
function sendReview(){
  const input = document.getElementById('input');
  const msg = input.value.trim();
  if(!msg) return;
  input.value = '';
  addMsg('user', msg);
  
  // 解析章节号
  const match = msg.match(/第(\d+)章?/);
  const chapter = match ? parseInt(match[1]) : 1;
  
  fetch('/api/review', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({session_id: sessionId, chapter, feedback: msg, action: 'rewrite'})
  }).then(r=>r.json()).then(data => {
    addMsg('ai', data.message || '已处理');
  }).catch(e => addMsg('ai', '错误: ' + e.message));
}

// ---- 面板更新 ----
function updatePanel(){
  const panel = document.getElementById('panelContent');
  if(!sessionId){ panel.innerHTML = '<div style="color:#555;font-size:13px">开始交互后显示</div>'; return; }
  fetch('/api/wb/result/' + sessionId).then(r=>r.json()).then(data => {
    if(data.world_description){
      document.getElementById('worldBadge').textContent = data.world_description.split('\\n')[0] || '世界';
    }
    let html = '<div style="font-size:12px;color:#888">';
    html += '<b>世界观:</b> ' + (data.world_description || '').substring(0,100) + '</div>';
    if(data.scene_map) html += '<div style="font-size:12px;color:#888;margin-top:8px"><b>场景:</b><br>' + data.scene_map.replace(/\\n/g,'<br>') + '</div>';
    if(data.protagonist && data.protagonist.name){
      html += '<div style="margin-top:8px"><b>角色:</b></div>';
      html += '<div class="item">' + data.protagonist.name + ' <span class="tag full">主角</span></div>';
      if(data.supporting) data.supporting.forEach(c => {
        html += '<div class="item">' + c.name + ' <span class="tag ' + (c.weight||'light') + '">' + (c.scene_role||'配角') + '</span></div>';
      });
      if(data.antagonist && data.antagonist.name){
        html += '<div class="item">' + data.antagonist.name + ' <span class="tag full">反派</span></div>';
      }
    }
    panel.innerHTML = html;
  }).catch(()=>{});
}

renderPhases();
addMsg('ai', '你好! 输入一句话, 我开始和你一起构建世界。\\\\n例如: "我想写一个修仙世界"');
</script>
</body>
</html>''')
print('OK Web UI 已更新')
