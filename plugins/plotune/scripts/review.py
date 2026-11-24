#!/usr/bin/env python3
"""Read-only structural review and graph impact preview for CSV/SQLite portable workspaces.

LLM/engineering assessment is required for semantics; this tool never writes records.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace import collect_sqlite, collect_csv, validate_records


def recs(backend,path):
    r,errors=(collect_sqlite if backend=='sqlite' else collect_csv)(path)
    errors+=validate_records(r)
    return r,errors


def nonempty(x):return str(x or '').strip()

def quality(r, product=None):
    if product and product not in {x['product_id'] for x in r.get('products',[])}:
        raise ValueError('Unknown product ID: '+product)
    findings=[]; reqs=[x for x in r.get('requirements',[]) if not product or x.get('product_id')==product]
    trace=r.get('traceability',[]); sources=r.get('stakeholder_needs',[])
    known={x['requirement_id'] for x in reqs}
    tests=r.get('test_cases',[])
    for x in reqs:
        rid=x['requirement_id'];rev=str(x.get('revision') or '')
        def f(check,title,description):findings.append({'check_id':check,'record_type':'Requirement','record_id':rid,'record_revision':rev,'title':title,'description':description,'classification':'Structural candidate','persistence':'Not saved'})
        if not nonempty(x.get('requirement')):f('RQ-01','Missing statement','Requirement statement is blank')
        if not nonempty(x.get('acceptance_criteria')):f('RQ-01','Missing acceptance criteria','Acceptance criteria not supplied; determine if this record is intended to be normative')
        if not nonempty(x.get('source_url')) and not nonempty(x.get('rationale')) and not any((z.get('from_id')==rid or z.get('to_id')==rid) and str(z.get('from_type','')).lower().replace('_',' ') in ('stakeholder need','need','requirement') for z in trace):
            f('RQ-02','Source context not recorded','No rationale, source link or recognized related need/requirement; review project Guide before calling this a defect')
        if not nonempty(x.get('revision')):f('RQ-03','Revision missing','Normative revision is required')
    normalized={}
    for x in reqs:
        text=' '.join(str(x.get('requirement') or '').lower().split())
        if text and text in normalized:
            findings.append({'check_id':'RQ-07','record_type':'Requirement','record_id':x['requirement_id'],'record_revision':str(x.get('revision') or ''),'title':'Exact duplicate-like wording','description':'Same normalized text as '+normalized[text]+'; inspect scope before deduplicating','classification':'Review candidate','persistence':'Not saved'})
        elif text:normalized[text]=x['requirement_id']
    orphan=[]
    endpoints={'requirement':{x['requirement_id'] for x in r.get('requirements',[])},'actor':{x['actor_id'] for x in r.get('actors',[])},'use case':{x['use_case_id'] for x in r.get('use_cases',[])},'test case':{x['test_case_id'] for x in tests},'stakeholder need':{x['need_id'] for x in sources},'change request':{x['change_id'] for x in r.get('change_requests',[])},'review finding':{x['finding_id'] for x in r.get('review_findings',[])}}
    for z in trace:
        for side in ('from','to'):
            kind=str(z.get(side+'_type') or '').strip().lower().replace('_',' ')
            key=z.get(side+'_id')
            if kind in endpoints and key not in endpoints[kind]:
                orphan.append({'side':side,'type':kind,'id':key,'relation':z.get('relation')})
    return {'reviewed_requirements':len(reqs),'findings':findings,'orphan_typed_links':orphan,'caveat':'Structural review only; LLM/human review needed for ambiguity, consistency, safety and actual ISO/VDA conformity. No findings saved.'}


def scope_requirements(r,product=None,baseline=None):
    if baseline:
        baselines={x['baseline_id']:x for x in r.get('baselines',[])}
        if baseline not in baselines:
            raise ValueError('Unknown baseline ID: '+baseline)
        if product and baselines[baseline].get('product_id') != product:
            raise ValueError('Baseline belongs to a different product: '+baseline)
        items=[x for x in r.get('baseline_items',[]) if x.get('baseline_id')==baseline]
        return [(x['requirement_id'],str(x.get('requirement_revision') or ''),x.get('requirement_snapshot') or '') for x in items]
    if product and product not in {x['product_id'] for x in r.get('products',[])}:
        raise ValueError('Unknown product ID: '+product)
    return [(x['requirement_id'],str(x.get('revision') or ''),x.get('requirement') or '') for x in r.get('requirements',[]) if not product or x.get('product_id')==product]


def coverage(r,product=None,baseline=None):
    scope=scope_requirements(r,product,baseline); cases=r.get('test_cases',[])
    executions=r.get('test_executions',[]); verifications=r.get('verification',[]); runs=r.get('verification_runs',[])
    data=[]
    for rid,rev,statement in scope:
        relevant=[c for c in cases if c.get('requirement_id')==rid and str(c.get('requirement_revision') or '')==rev]
        linked={c.get('test_case_id') for c in relevant}
        actual=[e for e in executions if e.get('requirement_id')==rid and str(e.get('requirement_revision') or '')==rev and (e.get('test_case_id') in linked)]
        ev=[v for v in verifications if v.get('requirement_id')==rid and str(v.get('requirement_revision') or '')==rev]
        vr=[v for v in runs if v.get('requirement_id')==rid and str(v.get('requirement_revision') or '')==rev]
        all_evidence=actual+ev+vr
        fails=[x for x in all_evidence if x.get('result') in ('FAIL','BLOCKED')]
        passes=[x for x in all_evidence if x.get('result')=='PASS']
        # An evidence narrative is useful historical context, but never a verified
        # artifact by itself. Missing coverage on an execution is not complete.
        linked_complete=[x for x in passes if nonempty(x.get('evidence_url')) and
                         (x in ev or str(x.get('coverage') or '').strip().lower() in ('complete','full'))]
        narratives_only=[x for x in passes if not nonempty(x.get('evidence_url')) and nonempty(x.get('evidence_summary'))]
        if fails: status='Fail/blocked evidence exists'
        elif linked_complete:status='PASS with linked evidence; acceptance/maturity review required'
        elif narratives_only:status='PASS with narrative only; independent artifact not linked'
        elif passes:status='Unsubstantiated or partial PASS; review required'
        elif all_evidence:status='Executed; no applicable PASS evidence'
        elif relevant:status='Defined, not exercised'
        else:status='No linked case'
        data.append({'requirement_id':rid,'revision':rev,'status':status,'linked_cases':len(relevant),
                     'executions':len(actual),'verification_records':len(ev)+len(vr),
                     'direct_verification_records':len(ev),
                     'pass_artifacts_linked':len(linked_complete),
                     'pass_narratives_without_link':len(narratives_only),
                     'acceptance_and_maturity_confirmed':False,
                     'historical_scope_note':'Only exact selected revision reviewed; evidence for another revision is not reclassified'})
    totals={status:sum(x['status']==status for x in data) for status in sorted({x['status'] for x in data})}
    return {'denominator':len(scope),'scope':{'product_id':product,'baseline_id':baseline},'counts':totals,'items':data,'caveat':'This is an evidence inventory, NOT a verified requirement verdict. PASS claims still require independent confirmation of artifact, acceptance coverage, configuration and maturity. Read-only.'}


def impact(r,rid,depth=3):
    reqs={x['requirement_id']:x for x in r.get('requirements',[])}
    if rid not in reqs:raise ValueError('Unknown requirement ID: '+rid)
    edges=[]; parent_rels={}
    for x in reqs.values():
        for p in str(x.get('parent_requirement_ids') or '').split(','):
            p=p.strip()
            if p: edges.append(('Requirement',x['requirement_id'],'Requirement',p,'Refines parent'))
    kinds={'requirements':'Requirement','actors':'Actor','use_cases':'Use Case','stakeholder_needs':'Stakeholder Need','test_cases':'Test Case','change_requests':'Change Request','review_findings':'Review Finding'}
    for z in r.get('traceability',[]):
        edges.append((str(z.get('from_type','')),str(z.get('from_id','')),str(z.get('to_type','')),str(z.get('to_id','')),str(z.get('relation',''))))
    def canon(k):return k.strip().lower().replace('_',' ').replace('stakeholder needs','stakeholder need').replace('requirements','requirement')
    start=('requirement',rid);seen={start:0};front=[start];relations=[]
    for step in range(depth):
        new=[]
        for node in front:
            for a,aid,b,bid,rel in edges:
                aa=(canon(a),aid);bb=(canon(b),bid)
                if node in (aa,bb):
                    other=bb if node==aa else aa
                    relations.append({'from_type':a,'from_id':aid,'relation':rel,'to_type':b,'to_id':bid})
                    if other not in seen and other[1]:seen[other]=step+1;new.append(other)
        front=new
        if not front:break
    impacted_reqs={key for kind,key in seen if kind=='requirement'}
    test_cases=[x for x in r.get('test_cases',[]) if x.get('requirement_id') in impacted_reqs or ('test case',x.get('test_case_id')) in seen]
    baseline_items=[x for x in r.get('baseline_items',[]) if x.get('requirement_id') in impacted_reqs]
    changes=[x for x in r.get('change_impacts',[]) if x.get('target_id') in impacted_reqs]
    findings=[x for x in r.get('review_findings',[]) if x.get('record_id') in impacted_reqs]
    return {'seed':{'id':rid,'revision':str(reqs[rid].get('revision') or '')},'depth':depth,'related_records':[{'type':a,'id':b,'distance':d} for (a,b),d in sorted(seen.items()) if (a,b)!=start], 'relations':list({json.dumps(x,sort_keys=True):x for x in relations}.values()),'affected_requirements':[{'id':i,'revision':str(reqs[i].get('revision') or '')} for i in sorted(impacted_reqs)],'test_cases':[{'id':x['test_case_id'],'requirement_id':x.get('requirement_id'),'revision':str(x.get('requirement_revision') or '')} for x in test_cases], 'baseline_items':[{'baseline_id':x.get('baseline_id'),'requirement_id':x.get('requirement_id'),'revision':str(x.get('requirement_revision') or '')} for x in baseline_items], 'review_findings':[x.get('finding_id') for x in findings],'recorded_change_impacts':[x.get('impact_id') for x in changes], 'caveat':'Candidate transitive impact, not proof of actual design/safety change. Verify each link, revision, interface and evidence manually. No writes.'}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('command',choices=['quality','coverage','impact'])
    ap.add_argument('--backend',required=True,choices=['csv','sqlite'])
    ap.add_argument('--path',required=True)
    ap.add_argument('--product-id')
    ap.add_argument('--baseline-id')
    ap.add_argument('--requirement-id')
    ap.add_argument('--depth',type=int,default=3)
    a=ap.parse_args()
    try:
        if a.depth<1 or a.depth>8:raise ValueError('depth must be between 1 and 8')
        r,errors=recs(a.backend,a.path)
        if errors:raise ValueError('Workspace integrity checks failed: '+'; '.join(errors[:12]))
        if a.command=='quality':result=quality(r,a.product_id)
        elif a.command=='coverage':result=coverage(r,a.product_id,a.baseline_id)
        else:
            if not a.requirement_id:raise ValueError('--requirement-id required')
            result=impact(r,a.requirement_id,a.depth)
        print(json.dumps(result,indent=2,ensure_ascii=False))
    except Exception as e:
        print('ERROR:',str(e),file=sys.stderr);raise SystemExit(1)
if __name__=='__main__':main()
