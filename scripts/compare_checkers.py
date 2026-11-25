"""Sequential bounded comparison; no HTTP server or parallel workers needed."""
import hashlib,json,os,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Pipeline,OpenAIModel,AppError
from local_config import load_env
from checker_dimensions import check as dimension_check
from checker_evidence import check as evidence_check
from scripts.evaluate_checker import load_cases,score

MAX_FILE=256*1024
MAX_OUTPUT=4*1024*1024
MAX_CALLS=24
MEMORY_BYTES=192*1024*1024

def peak_bytes():
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss if sys.platform=='darwin' else rss*1024

def guard():
    peak=peak_bytes()
    if peak>MEMORY_BYTES:raise RuntimeError('Memory budget exceeded; stopped without retry')
    return peak

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--validate-only',action='store_true')
    parser.add_argument('--experiment',choices=['dimensions','evidence'],default='dimensions')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    cases=[]; hashes={}
    for name in ['checker-fixed-v1.json','checker-transfer-v1.json']:
        p=root/'evals'/name
        if p.stat().st_size>MAX_FILE:raise SystemExit('Dataset too large')
        dataset=load_cases(p)
        if len(dataset['cases'])>12:raise SystemExit('Too many cases')
        for case in dataset['cases']:case['split']=dataset['split']
        cases+=dataset['cases'];hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    if len(cases)*2>MAX_CALLS:raise SystemExit('Call budget exceeded')
    for c in cases:
        if len(json.dumps(c['request']).encode())>32768:raise SystemExit('Context too large')
    guard()
    if args.validate_only:print(f'{len(cases)} cases, maximum {len(cases)*2} sequential calls, 192 MiB peak-RSS cap');return
    load_env();model=OpenAIModel();pipeline=Pipeline(model)
    if not model.ready:raise SystemExit('Missing local model configuration')
    output=Path(args.output)
    report=dict(experiment=args.experiment,model=os.environ['OPENAI_MODEL'],dataset_hashes=hashes,
        source_hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['core.py','checker_'+args.experiment+'.py','scripts/compare_checkers.py']},
        limits=dict(max_calls=MAX_CALLS,memory_bytes=MEMORY_BYTES,response_bytes=1024*1024,output_bytes=MAX_OUTPUT),
        label_source='assistant-authored, not independently reviewed',results=[],calls_attempted=0)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as f:json.dump(report,f)
    try:
        for i,case in enumerate(cases):
            # Alternate which checker goes first to avoid one fixed ordering.
            for variant in (['baseline',args.experiment] if i%2==0 else [args.experiment,'baseline']):
                before=guard();start=time.monotonic()
                row=dict(id=case['id'],split=case['split'],variant=variant,peak_before=before)
                report['calls_attempted']+=1
                try:
                    body=case['request']
                    if variant=='baseline':response=pipeline.check(body)
                    else:response=(dimension_check if args.experiment=='dimensions' else evidence_check)(model,pipeline.prepare(body),body['candidates'][0])
                    row['response']=response
                except Exception as exc:
                    row['error']={'stage':'check','message':str(exc)}
                row['seconds']=round(time.monotonic()-start,3);row['peak_after']=peak_bytes()
                report['results'].append(row)
                if row['peak_after']>MEMORY_BYTES:raise RuntimeError('Memory budget exceeded')
                if 'error' in row:raise RuntimeError('Check failed; no automatic retry')
                persist(output,report,cases)
                print(case['id'],variant,'complete',round(row['peak_after']/1024/1024,1),'MiB',flush=True)
    except Exception as exc:
        report['stopped']=str(exc)
    persist(output,report,cases)
    print(json.dumps(report['scores'],ensure_ascii=False))
    if report.get('stopped'):raise SystemExit(report['stopped'])

def persist(output,report,cases):
    report['scores']={}
    for split in ['development','transfer']:
        subset=[c for c in cases if c['split']==split]
        for variant in ['baseline',report['experiment']]:
            rows=[r for r in report['results'] if r['variant']==variant and r['split']==split]
            report['scores'][split+'_'+variant]=score(subset,rows)['counts']
    report['uncertain_verdicts']=sum(len(r.get('response',{}).get('uncertain_dimensions',[])) for r in report['results'])
    encoded=json.dumps(report,ensure_ascii=False,indent=2).encode()
    if len(encoded)>MAX_OUTPUT:raise RuntimeError('Evidence size limit exceeded; stopped')
    output.write_bytes(encoded)

if __name__=='__main__':main()
