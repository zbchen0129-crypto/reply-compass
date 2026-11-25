"""Bounded, deterministic paste normalization. Never infers a person's identity."""
import re
from core import AppError


def normalize(body):
    text=body.get('text'); mode=body.get('mode','conversation'); me=body.get('self_name')
    if not isinstance(text,str) or not text.strip() or len(text)>18000:
        raise AppError('请输入 1–18,000 字符。')
    if len(text.splitlines())>240:raise AppError('行数过多，请只粘贴最近相关的对话。')
    if mode=='incoming':
        return {'names':[],'messages':[{'name':'对方','text':' '.join(text.splitlines()).strip()}],
                'canonical':'对方：'+' '.join(text.splitlines()).strip(), 'needs_identity':False,
                'notice':'这段内容将作为对方的一条消息；换行已合并，请核对。'}
    if mode!='conversation':raise AppError('输入模式无效。')
    messages=[]
    for number,raw in enumerate(text.splitlines(),1):
        line=raw.strip()
        if not line:continue
        # Explicit bracketed date/time only. Never strip arbitrary bracketed content.
        line=re.sub(r'^\[[\d/:, .APMapm-]{4,40}\]\s*','',line)
        match=re.match(r'^([^:：\n]{1,40})[:：]\s*(.*)$',line)
        if not match:
            raise AppError(f'第 {number} 行无法识别。请保留“姓名：消息”格式；单条消息可切换到单条模式。')
        name,content=match[1].strip(),match[2].strip()
        if not content or not name or name.isdigit() or name.lower() in ('http','https'):
            raise AppError(f'第 {number} 行姓名或消息无效，请检查。')
        messages.append({'name':name,'text':content})
    if not 1<=len(messages)<=80:raise AppError('请粘贴 1–80 条消息。')
    names=list(dict.fromkeys(m['name'] for m in messages))
    if len(names)>2:raise AppError('目前只支持双人聊天，请先筛选相关两人的消息。')
    automatic={'我':'self','self':'self','对方':'other','other':'other'}
    standard=all(n in automatic for n in names)
    if not standard and me is not None and me not in names:raise AppError('所选姓名不在聊天中。')
    mapping=automatic if standard else {n:'self' if n==me else 'other' for n in names}
    canonical=None if not standard and me is None else '\n'.join(('我' if mapping[m['name']]=='self' else '对方')+'：'+m['text'] for m in messages)
    return dict(names=names,messages=messages,canonical=canonical,needs_identity=canonical is None,
                notice='请核对消息顺序和双方身份。此整理步骤仅在本机运行，不调用模型。')
