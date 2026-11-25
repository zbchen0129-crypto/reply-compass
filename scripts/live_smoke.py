import json,time,urllib.request,urllib.error,pathlib
import argparse
parser=argparse.ArgumentParser(description="Run three synthetic live smoke cases (9 model calls).")
parser.add_argument("--output", required=True)
parser.add_argument("--version", default="v3")
parser.add_argument("--cases", help="Optional synthetic case JSON file")
args=parser.parse_args()
output_path=pathlib.Path(args.output)
if output_path.exists(): raise SystemExit("Refusing to overwrite existing evidence")
output_path.parent.mkdir(parents=True,exist_ok=True)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def post(path,body):
 req=urllib.request.Request('http://127.0.0.1:8765/api/'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 with opener.open(req,timeout=105) as r:return json.load(r)
cases=[('invitation','我：This week is busy. I might be free Saturday, but I’m not sure yet.\n对方：Dinner Saturday? 🙂 You pick the place this time.',['答应','拒绝','先澄清']),('help','我：Friday is already packed for me.\n对方：Could you help me move on Friday? Even an hour would help.',['拒绝','有条件答应','提出替代方案']),('emoji','我：Could you take another look at the draft today?\n对方：Sure 🙂',['简单致谢','先澄清','暂缓决定'])]
if args.cases:
 cases=[(c["id"],c["chat"],c["directions"]) for c in json.loads(pathlib.Path(args.cases).read_text())]
with opener.open("http://127.0.0.1:8765/api/status",timeout=5) as response: status=json.load(response)
if not status["ready"]: raise SystemExit("Model is not configured")
if status.get("prompt_version") != args.version: raise SystemExit("Restart backend: expected "+args.version+", got "+str(status.get("prompt_version")))
results=[]
for name,chat,directions in cases:
 start=time.monotonic()
 try:
  extracted=post('extract',{'chat':chat})
  output=post('generate',{'chat':chat,'context':extracted['context'],'directions':directions,'preferences':{'tone':'warm','emoji':True,'language':'English'}})
  if output.get('prompt_version') != args.version: raise RuntimeError('Unexpected prompt version: '+str(output.get('prompt_version')))
  result=dict(case=name,chat=chat,extracted=extracted,output=output,seconds=round(time.monotonic()-start,2))
 except urllib.error.HTTPError as e:result=dict(case=name,error=e.read().decode(),status=e.code)
 except Exception as e:result=dict(case=name,error=str(e))
 results.append(result)
 print(json.dumps(result,ensure_ascii=False),flush=True)
 output_path.write_text(json.dumps({'model':status['model'],'expected_prompt_version':args.version,'preferences':{'tone':'warm','emoji':True,'language':'English'},'directions_by_case':{n:d for n,c,d in cases},'synthetic_data':True,'results':results},ensure_ascii=False,indent=2))
 if 'error' in result:break
