(() => {
  const el = id => document.getElementById(id);
  let extracted = null, originalChat = '', busy = false, ready = false, canNormalize = false;
  const directions = ['答应','有条件答应','拒绝','提出替代方案','先澄清','简单致谢','暂缓决定'];
  const controlIds = ['input-mode','normalize','identity','normalized-chat','chat-input','extract','generate','live-tone','live-language','live-emoji'];
  function setBusy(value) {
    busy = value;
    for (const id of controlIds) el(id).disabled = value || (id === 'extract' && (!ready || !el('normalized-chat').value.trim())) || (id === 'normalize' && !canNormalize);
    for (const input of document.querySelectorAll('#context-editor textarea, #context-editor select, #live-directions input')) input.disabled = value;
  }
  function clearResults() { el('live-results').replaceChildren(); }
  async function api(path, body) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 110000);
    try {
      const r = await fetch(path, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:controller.signal});
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || '请求失败。');
      return data;
    } catch (e) {
      if (e.name === 'AbortError') throw new Error('请求超时，请重试。');
      throw e;
    } finally { clearTimeout(timer); }
  }
  directions.forEach((name, i) => {
    const label = document.createElement('label'), input = document.createElement('input');
    input.type = 'checkbox'; input.value = name; input.checked = [0,2,4].includes(i);
    input.onchange = clearResults; label.append(input, document.createTextNode(name)); el('live-directions').append(label);
  });
  function invalidate(){extracted=null;el('review').hidden=true;clearResults();}
  el('chat-input').oninput = () => {el('paste-review').hidden=true;el('normalized-chat').value=''; extracted = null; el('review').hidden = true; clearResults(); el('live-status').textContent = '聊天已更改，请重新分析。'; };
  el('input-mode').onchange=()=>el('chat-input').oninput();
  el('normalized-chat').oninput=()=>{invalidate();setBusy(false);el('live-status').textContent='预览已修改，请确认后分析。';};
  async function normalizePaste(selfName){
    if(busy)return;
    invalidate();setBusy(true);el('live-status').textContent='正在本机整理…';
    try{
      const body={text:el('chat-input').value,mode:el('input-mode').value};
      if(selfName)body.self_name=selfName;
      const result=await api('/api/normalize',body);
      el('paste-review').hidden=false;el('paste-notice').textContent=result.notice;
      el('identity-label').hidden=!result.needs_identity && !selfName;
      if(!selfName){
        el('identity').replaceChildren();const blank=document.createElement('option');blank.value='';blank.textContent='请选择你的名字';el('identity').append(blank);
        result.names.forEach(name=>{const option=document.createElement('option');option.value=name;option.textContent=name;el('identity').append(option);});
      }
      el('normalized-chat').value=result.canonical || '';
      el('live-status').textContent=result.needs_identity?'请选择哪个人是你，再核对对话。':'整理完成，请核对后点击确认并分析。';
    }catch(e){el('paste-review').hidden=true;el('normalized-chat').value='';el('live-status').textContent=e.message;}
    finally{setBusy(false);}
  }
  el('normalize').onclick=()=>normalizePaste();
  el('identity').onchange=()=>{el('normalized-chat').value='';invalidate();setBusy(false);if(el('identity').value)normalizePaste(el('identity').value);};
  for (const id of ['live-tone','live-language','live-emoji']) el(id).onchange = () => { clearResults(); el('live-status').textContent = '偏好已更改，请重新生成。'; };
  el('extract').onclick = async () => {
    if (busy) return;
    clearResults(); el('review').hidden = true; extracted = null;
    setBusy(true); el('live-status').textContent = '正在提取上下文…';
    try {
      originalChat = el('normalized-chat').value;
      extracted = await api('/api/extract', {chat:originalChat});
      if(extracted.prompt_version !== 'v3') {extracted=null;throw new Error('后端仍是旧版本，请在原终端重启 python3 server.py，再刷新页面。');}
      el('live-messages').replaceChildren(...extracted.messages.map(m => {
        const p = document.createElement('p'); p.id = `live-${m.id}`; p.textContent = `${m.id} · ${m.speaker === 'self' ? '我' : '对方'}：${m.text}`; return p;
      }));
      el('context-editor').replaceChildren(...extracted.context.items.map(item => {
        const label = document.createElement('div'); label.className = 'context-edit';
        const title = document.createElement('span'); title.textContent = `${item.kind} · `; label.append(title);
        item.source_message_ids.forEach(id => {const a = document.createElement('a'); a.href = `#live-${id}`; a.textContent = `来源 ${id} `; label.append(a);});
        const input = document.createElement('textarea'); input.value = item.text; input.rows = 2; input.setAttribute('aria-label', `${item.id} 摘要文本`);
        input.oninput = () => {item.text = input.value; clearResults();}; label.append(input);
        const roleNames = {subject:'这是谁的状态',requester:'谁提出请求',actor:'谁执行行动',recipient:'谁接受帮助'};
        const people = {self:'我',other:'对方',both:'双方',unknown:'尚不确定',not_applicable:'不适用'};
        const roles = document.createElement('div'); roles.className='controls';
        Object.entries(roleNames).forEach(([key,name]) => {
          const field=document.createElement('label'); field.textContent=name;
          const select=document.createElement('select'); select.setAttribute('aria-label',`${item.id} ${name}`);
          Object.entries(people).forEach(([value,text])=>{const option=document.createElement('option');option.value=value;option.textContent=text;select.append(option);});
          select.value=item.roles[key]; select.onchange=()=>{item.roles[key]=select.value;clearResults();el('live-status').textContent='角色已修改，请重新生成。';};field.append(select);roles.append(field);
        });label.append(roles);return label;
      }));
      el('review').hidden = false; el('live-status').textContent = '请核对摘要和消息来源，必要时修改，再生成回复。';
    } catch(e) { el('live-status').textContent = e.message; }
    finally { setBusy(false); }
  };
  el('generate').onclick = async () => {
    if (busy || !extracted) return;
    const selected = [...document.querySelectorAll('#live-directions input:checked')].map(x=>x.value);
    if (!selected.length || selected.length > 3) {el('live-status').textContent='请选择 1–3 个回复方向。';return;}
    clearResults(); setBusy(true); el('live-status').textContent = '正在生成并检查回复，可能需要一分钟…';
    try {
      const result = await api('/api/generate', {chat:originalChat, context:extracted.context, directions:selected,
        preferences:{tone:el('live-tone').value, language:el('live-language').value, emoji:el('live-emoji').checked}});
      result.replies.forEach((reply,i) => {
        const card = document.createElement('article'); card.className = 'reply live-card';
        const h = document.createElement('h3'); h.textContent = reply.direction;
        const text = document.createElement('p'); text.className = 'generated-text'; text.textContent = reply.text;
        card.append(h,text);
        for (const [label,items] of [['新增承诺',reply.introduced_commitments],['需要确认',reply.assumptions]]) {
          if(items.length){const p=document.createElement('p');p.textContent=`${label}：${items.join('；')}`;card.append(p);}
        }
        const warnings = result.checks.filter(c=>c.reply_index===i);
        const notes=document.createElement('p'); notes.textContent=warnings.length ? warnings.map(c=>`${({role_conflict:'人物关系不一致',stance_conflict:'立场不一致',unsupported_fact:'缺乏依据',missing_answer:'尚未回答',new_commitment:'新增承诺提醒'})[c.type] || c.type}：${c.explanation}`).join('\n') : '模型检查暂未发现问题，仍请确认后使用。';card.append(notes);
        const b=document.createElement('button');b.type='button';b.textContent='复制这条';b.onclick=async()=>{try{await navigator.clipboard.writeText(reply.text);el('live-status').textContent='已复制。';}catch{el('live-status').textContent='请手动选择回复文字复制。';}};card.append(b);el('live-results').append(card);
      });
      el('live-status').textContent='已生成并完成模型检查；请核对事实和承诺。';
    } catch(e) {el('live-status').textContent=e.message;}
    finally {setBusy(false);}
  };
  el('extract').disabled=true;el('normalize').disabled=true;
  fetch('/api/status').then(r=>{if(!r.ok)throw new Error();return r.json();}).then(data=>{
    canNormalize=(data.capabilities || []).includes('paste_v1');
    ready=data.ready && canNormalize && data.prompt_version === 'v3';
    if(!canNormalize){el('model-status').textContent='请重启后端以加载聊天整理功能。';setBusy(false);return;}
    if(data.prompt_version !== 'v3'){el('model-status').textContent='代码已更新：请重启后端并刷新页面以加载 v3。';setBusy(false);return;} el('model-status').textContent=ready ? `模型已配置：${data.model}（尚不代表已验证调用成功）` : '后端已连接。请在服务端配置 OPENAI_API_KEY 和 OPENAI_MODEL 后重启。'; setBusy(false);
  }).catch(()=>{el('model-status').textContent='未连接后端，请使用 python3 server.py 启动后访问本地地址。';});
})();
