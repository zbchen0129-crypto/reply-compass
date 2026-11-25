const cases = [
  {title:'01 · 周末邀约', messages:[['self','This week is busy. I might be free Saturday, but I’m not sure yet.'],['other','Dinner Saturday? 🙂 You pick the place this time.']],context:[['待定','你还没有确认周六是否有空。',0],['待回答','是否参加晚餐，以及是否负责选餐厅。',1]],replies:[
    {label:'答应',brief:'Saturday works. I’ll pick a place.',warm:'Yes, let’s do Saturday! I’d be happy to pick a place.',emoji:'🙂',impact:'新增承诺：确认周六参加，并负责选餐厅。请先确认自己有空；具体时间仍未确定。'},
    {label:'有条件答应',brief:'Can I confirm tomorrow? If I can make it, I’ll pick a place.',warm:'I’d love to join! Can I confirm tomorrow? If I can make it, I’m happy to pick a place.',emoji:'🙂',impact:'尚未确认参加；提出明天确认，且仅在参加时负责选餐厅。请确认明天能够给出答复。'},
    {label:'拒绝',brief:'I can’t make it Saturday.',warm:'Thanks for inviting me! I won’t be able to make it Saturday.',emoji:'🙏',impact:'明确拒绝本次邀约；没有编造理由，也没有承诺下次安排。'}]},
  {title:'02 · 请求帮忙',messages:[['self','Friday is already packed for me.'],['other','Could you help me move on Friday? Even an hour would help.']],context:[['事实','你此前说周五已经很忙。',0],['待回答','是否能在周五帮忙搬家，哪怕一小时。',1]],replies:[
    {label:'拒绝',brief:'I can’t help on Friday.',warm:'I’m sorry, I can’t help on Friday. I hope the move goes smoothly.',emoji:'🙏',impact:'保留明确拒绝的立场。温暖版本也不暗示会尝试抽时间。'},
    {label:'有条件答应',brief:'I can help for one hour on Friday, but no longer.',warm:'I can make one hour work on Friday. I’m sorry I can’t stay longer.',emoji:'🙂',impact:'新增承诺：周五提供一小时帮助。相较此前“很忙”改变了安排，需要你确认能够做到。'},
    {label:'提出替代',brief:'I can’t do Friday. Would Sunday help? I’d need to check my availability.',warm:'I’m sorry Friday won’t work. Would Sunday be useful? I’d need to check whether I’m free.',emoji:'🙂',impact:'提出周日作为待确认的替代日期；聊天没有提供周日是否有空的信息，未替你确认。'}]},
  {title:'03 · Sure 🙂',messages:[['self','Could you take another look at the draft today?'],['other','Sure 🙂']],context:[['文字事实','对方在文字上表示同意再看草稿。',1],['不确定','具体完成时间未说明；无法仅凭 🙂 确认对方情绪。',1]],replies:[
    {label:'确认时间',brief:'Thanks. Would you be able to send your notes by 3 pm today?',warm:'Thanks, I appreciate it! Would you be able to send your notes by 3 pm today?',emoji:'🙂',impact:'提出新的时间请求：今天下午三点。原聊天没有这个时间，请按实际需要修改；对方尚未确认。'},
    {label:'简单致谢',brief:'Thanks!',warm:'Thank you, I really appreciate your help!',emoji:'🙂',impact:'表达感谢，没有新增时间约定。具体何时完成仍不确定。'},
    {label:'放宽时间',brief:'Thanks. Tomorrow is fine too if today is busy.',warm:'Thank you! If today is busy, tomorrow would work for me too.',emoji:'🙂',impact:'将你可接受的时间放宽至明天。仅在你确实可以等到明天时使用。'}]}
];
let caseIndex=0, replyIndex=0;
const $=id=>document.getElementById(id);
function makeButton(label,selected,handler){const b=document.createElement('button');b.type='button';b.textContent=label;b.setAttribute('aria-pressed',String(selected));b.onclick=handler;return b;}
function renderCase(){
  $('scenarios').replaceChildren(...cases.map((c,i)=>makeButton(c.title,i===caseIndex,()=>{caseIndex=i;replyIndex=0;renderCase();})));
  const current=cases[caseIndex];
  $('messages').replaceChildren(...current.messages.map(([who,text],i)=>{const box=document.createElement('div');box.className=`message ${who}`;box.id=`message-${i}`;const label=document.createElement('div');label.className='speaker';label.textContent=who==='self'?'你':'对方';const bubble=document.createElement('div');bubble.className='bubble';bubble.textContent=text;box.append(label,bubble);return box;}));
  $('context').replaceChildren(...current.context.map(([kind,text,source])=>{const row=document.createElement('div');row.className='context-item';const label=document.createElement('strong');label.textContent=`${kind} · `;const link=document.createElement('a');link.href=`#message-${source}`;link.textContent=`查看来源 #${source+1}`;row.append(label,document.createTextNode(text),link);return row;}));
  renderReply();
}
function renderReply(){const current=cases[caseIndex];$('directions').replaceChildren(...current.replies.map((r,i)=>makeButton(r.label,i===replyIndex,()=>{replyIndex=i;renderReply();})));const r=current.replies[replyIndex];$('reply').textContent=r[$('tone').value]+($('emoji').checked?' '+r.emoji:'');$('impact').textContent=r.impact;$('feedback').textContent='';}
$('tone').onchange=renderReply;$('emoji').onchange=renderReply;
$('copy').onclick=async()=>{try{await navigator.clipboard.writeText($('reply').textContent);$('feedback').textContent='已复制，可以自行修改后发送。';}catch{$('feedback').textContent='浏览器未允许复制，请选择上方文字手动复制。';}};
renderCase();
