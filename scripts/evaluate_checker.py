"""Fixed-candidate checker evaluation; never sends expected labels to the model."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Pipeline, AppError

ERROR_TYPES = {'role_conflict','stance_conflict','unsupported_fact','missing_answer'}


def score(cases, results):
    expected = {c['id']: set(c['expected_error_types']) for c in cases}
    counts = dict(true_positive=0,false_positive=0,true_negative=0,false_negative=0,
                  completed=0,failed=0,target_hits=0,target_total=0)
    rows=[]
    for result in results:
        want=expected[result['id']]
        if 'error' in result:
            counts['failed']+=1
            rows.append({'id':result['id'],'outcome':'call_failed'})
            continue
        found={c['type'] for c in result['response']['checks']} & ERROR_TYPES
        counts['completed']+=1
        outcome=('true_positive' if found else 'false_negative') if want else ('false_positive' if found else 'true_negative')
        counts[outcome]+=1
        counts['target_total']+=len(want)
        counts['target_hits']+=len(want & found)
        rows.append({'id':result['id'],'outcome':outcome,'expected':sorted(want),'reported':sorted(found), 'target_type_detected':want.issubset(found)})
    counts['not_run']=len(cases)-len(results)
    counts['false_positive_denominator']=counts['false_positive']+counts['true_negative']
    counts['false_negative_denominator']=counts['false_negative']+counts['true_positive']
    return {'counts':counts,'rows':rows}


def load_cases(path):
    dataset=json.loads(path.read_text())
    ids=[c['id'] for c in dataset['cases']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate case ids')
    for case in dataset['cases']:
        if not set(case['expected_error_types']).issubset(ERROR_TYPES):raise ValueError('Invalid expected label')
        body=case['request']; data=Pipeline().prepare(body)
        Pipeline().validate_candidates({'replies':body['candidates']},data)
        if len(body['candidates'])!=1:raise ValueError('One fixed candidate per case required')
    return dataset


def main():
    parser=argparse.ArgumentParser(description='8 fixed synthetic candidates, one checker call each; API usage applies.')
    parser.add_argument('--dataset',default='evals/checker-fixed-v1.json')
    parser.add_argument('--output')
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args()
    path=Path(args.dataset);dataset=load_cases(path)
    if args.validate_only:
        print(f"Validated {len(dataset['cases'])} cases; no model calls.");return
    if not args.output:parser.error('--output required for a live run')
    output=Path(args.output)
    if output.exists():parser.error('Refusing to overwrite evidence')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open('http://127.0.0.1:8765/api/status',timeout=5) as response:status=json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise SystemExit('Local server unavailable. Start python3 server.py in the configured terminal. No model calls made.') from None
    if not status.get('ready') or 'checker_v1' not in status.get('capabilities',[]):
        raise SystemExit('Restart server.py in the original terminal: checker_v1 is not ready. No model calls made.')
    report={'dataset_version':dataset['dataset_version'],'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'label_author':dataset['label_author'],'split':dataset['split'],'server':status,'results':[],
            'limitations':'Development cases; assistant-authored labels; no independent review. Raw type-based scores need explanation review.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    # Reserve evidence before paid calls; subsequent checkpoints update only this run.
    with output.open('x') as f:json.dump(report,f)
    for case in dataset['cases']:
        start=time.monotonic()
        try:
            request=urllib.request.Request('http://127.0.0.1:8765/api/check',data=json.dumps(case['request']).encode(),headers={'Content-Type':'application/json'})
            with opener.open(request,timeout=60) as response:body=json.load(response)
            if body.get('check_status')!='completed' or body.get('prompt_version')!=status['prompt_version']:raise ValueError('Unexpected check status/version')
            result={'id':case['id'],'response':body}
        except urllib.error.HTTPError as exc:
            result={'id':case['id'],'error':{'stage':'check','status':exc.code,'message':exc.read().decode()}}
        except (urllib.error.URLError,TimeoutError,ValueError) as exc:
            result={'id':case['id'],'error':{'stage':'check','message':str(exc)}}
        result['seconds']=round(time.monotonic()-start,3)
        report['results'].append(result);report['score']=score(dataset['cases'],report['results'])
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(case['id'], 'failed' if 'error' in result else 'completed',flush=True)
        if 'error' in result:break # preserve partial run; no silent retries
    print(json.dumps(report['score']['counts'],ensure_ascii=False))
    if any('error' in r for r in report['results']):raise SystemExit(1)

if __name__=='__main__':main()
