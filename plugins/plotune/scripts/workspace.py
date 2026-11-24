#!/usr/bin/env python3
"""Offline portable workspace initializer and structural validator (SQLite/CSV)."""
import argparse,csv,json,sqlite3,sys,shutil,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODEL=json.loads((ROOT/'schema/data-model.json').read_text(encoding='utf-8'))
TABLES=MODEL['tables']

def init_sqlite(path,wid):
    path=Path(path)
    if path.exists():raise ValueError('Refusing to overwrite existing database')
    path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as db:
        db.executescript((ROOT/'templates/sqlite/schema.sql').read_text())
        db.execute('INSERT INTO workspace_meta(schema_version,workspace_id) VALUES (?,?)',(MODEL['schema_version'],wid))
        db.commit()
    print('Initialized SQLite workspace:',path)

def init_csv(path,wid):
    path=Path(path)
    if path.exists() and any(path.iterdir()):raise ValueError('Refusing to populate nonempty directory')
    path.mkdir(parents=True,exist_ok=True)
    for f in (ROOT/'templates/csv').glob('*.csv'):shutil.copy2(f,path/f.name)
    (path/'workspace.json').write_text(json.dumps({'schema_version':MODEL['schema_version'],'workspace_id':wid},indent=2)+'\n')
    print('Initialized CSV workspace:',path)

def collect_sqlite(path):
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA foreign_keys=ON')
        errors=[f'SQLite FK violation: {row}' for row in db.execute('PRAGMA foreign_key_check')]
        meta=db.execute('SELECT schema_version,workspace_id FROM workspace_meta').fetchall()
        if len(meta)!=1 or meta[0][0]!=MODEL['schema_version']:errors.append('Missing/incorrect workspace_meta version')
        records={}
        for n,desc in TABLES.items():
            cols=[r[1] for r in db.execute(f'PRAGMA table_info({n})')]
            if cols!=desc['columns']:errors.append('Column mismatch in '+n)
            if cols:records[n]=[dict(zip(cols,r)) for r in db.execute(f'SELECT * FROM {n}')]
        return records,errors

def collect_csv(path):
    path=Path(path)
    errors=[];records={}
    f=path/'workspace.json'
    if not f.is_file():errors.append('Missing workspace.json')
    else:
        try:
            meta=json.loads(f.read_text())
            if meta.get('schema_version')!=MODEL['schema_version']:errors.append('Wrong schema version')
        except (ValueError,OSError):errors.append('Invalid workspace.json')
    for n,desc in TABLES.items():
        f=path/(n+'.csv')
        if not f.is_file():errors.append('Missing '+f.name);continue
        with f.open(newline='',encoding='utf-8-sig') as h:
            rd=csv.DictReader(h)
            if rd.fieldnames!=desc['columns']:errors.append('Column mismatch in '+f.name)
            records[n]=list(rd)
    return records,errors

def validate_records(records):
    errors=[]
    ids={}
    for table,desc in TABLES.items():
        rows=records.get(table,[]);key=desc['primary_key']
        if key:
            seen=set()
            for row in rows:
                t=tuple(str(row.get(k,'')) for k in key)
                if not all(t):errors.append('Blank key in '+table)
                if t in seen:errors.append('Duplicate key in '+table+': '+str(t))
                seen.add(t)
            ids[table]={tuple(str(r.get(k,'')) for k in key) for r in rows}
    products={k[0] for k in ids.get('products',set())};reqs={k[0] for k in ids.get('requirements',set())}
    for table in ('stakeholder_needs','actors','use_cases','requirements','decisions','baselines','change_requests','review_findings','standards_profiles'):
        for r in records.get(table,[]):
            p=r.get('product_id','')
            if p and p not in products:errors.append('Unknown product '+p+' in '+table)
    parents={}
    for r in records.get('requirements',[]):
        rid=str(r['requirement_id']);prs=[s.strip() for s in str(r.get('parent_requirement_ids') or '').split(',') if s.strip()]
        if rid in prs:errors.append('Self-parent '+rid)
        if len(prs)!=len(set(prs)):errors.append('Duplicate parent '+rid)
        for p in prs:
            if p not in reqs:errors.append('Unknown parent '+p+' for '+rid)
        parents[rid]=prs
        try:
            rev=int(r.get('revision') or 0)
            if rev<1:errors.append('Invalid revision for '+rid)
        except ValueError:errors.append('Invalid revision for '+rid)
    visited=set();active=set()
    def visit(node):
        if node in active:errors.append('Hierarchy cycle at '+node);return
        if node in visited:return
        active.add(node)
        for p in parents.get(node,[]):
            if p in parents:visit(p)
        active.remove(node);visited.add(node)
    for node in parents:visit(node)
    for table in ('verification','verification_runs','test_cases','test_executions','requirement_revisions','applicability','baseline_items'):
        for r in records.get(table,[]):
            req=r.get('requirement_id','')
            if req and req not in reqs:errors.append('Unknown requirement '+req+' in '+table)
    baselines={b['baseline_id']:b for b in records.get('baselines',[])}
    req_by_id={r['requirement_id']:r for r in records.get('requirements',[])}
    for r in records.get('baseline_items',[]):
        b=baselines.get(r['baseline_id'])
        if not b:errors.append('Orphan baseline item '+r['baseline_id']);continue
        if b['status']=='Frozen':
            if not r.get('requirement_snapshot') or not r.get('acceptance_criteria_snapshot'):
                errors.append('Incomplete frozen snapshot '+r['baseline_id']+'/'+r['requirement_id'])
            current=req_by_id.get(r['requirement_id'])
            if current and str(current.get('revision') or '')==str(r.get('requirement_revision') or ''):
                if str(current.get('requirement') or '')!=str(r.get('requirement_snapshot') or '') or str(current.get('acceptance_criteria') or '')!=str(r.get('acceptance_criteria_snapshot') or ''):
                    errors.append('Frozen snapshot differs from same-revision current requirement '+r['baseline_id']+'/'+r['requirement_id'])
    for r in records.get('verification',[]):
        if r.get('result')=='PASS' and not r.get('evidence_url') and not r.get('evidence_summary'):
            errors.append('PASS without evidence '+r['verification_id'])
    # Continuous Engineering extensions: conservative integrity checks, not arbitrary certification.
    changes={r['change_id'] for r in records.get('change_requests',[])}
    profiles={r['profile_id'] for r in records.get('standards_profiles',[])}
    known={'requirement':reqs,
           'actor':{r['actor_id'] for r in records.get('actors',[])},
           'use case':{r['use_case_id'] for r in records.get('use_cases',[])},
           'test case':{r['test_case_id'] for r in records.get('test_cases',[])},
           'change request':changes,
           'review finding':{r['finding_id'] for r in records.get('review_findings',[])},
           'stakeholder need':{r['need_id'] for r in records.get('stakeholder_needs',[])}}
    for r in records.get('review_findings',[]):
        ident=r['finding_id'];cr=r.get('change_request_id')
        if cr and cr not in changes:errors.append('Unknown change request for finding '+ident)
        prof=r.get('standard_profile_id')
        if prof and prof not in profiles:errors.append('Unknown standards profile for finding '+ident)
        kind=str(r.get('record_type','')).strip().lower().replace('_',' ')
        if kind in known and r.get('record_id') and r['record_id'] not in known[kind]:
            errors.append('Unknown finding target '+kind+': '+r['record_id'])
        if str(r.get('status'))=='Closed' and not str(r.get('resolution_notes') or '').strip():
            errors.append('Closed finding missing resolution '+ident)
    for r in records.get('change_impacts',[]):
        ident=r['impact_id'];cr=r.get('change_id')
        if cr not in changes:errors.append('Unknown change request for impact '+ident)
        kind=str(r.get('target_type','')).strip().lower().replace('_',' ')
        if kind in known and r.get('target_id') and r['target_id'] not in known[kind]:
            errors.append('Unknown change impact target '+kind+': '+r['target_id'])
        if kind=='requirement' and not str(r.get('target_revision') or '').strip():
            errors.append('Missing revision for requirement impact '+ident)
    for r in records.get('change_requests',[]):
        if r.get('baseline_id') and r['baseline_id'] not in baselines:
            errors.append('Unknown change baseline '+r['baseline_id'])
        if r.get('status')=='Closed' and not str(r.get('decision') or '').strip():
            errors.append('Closed change missing decision '+r['change_id'])
    return errors

def migrate_workspace(backend,path,apply=False):
    path=Path(path)
    old='1.0.0'; new=MODEL['schema_version']
    if backend=='sqlite':
        if not path.is_file():raise ValueError('SQLite workspace not found')
        with sqlite3.connect(path) as db:
            rows=db.execute('SELECT schema_version, workspace_id FROM workspace_meta').fetchall()
            if len(rows)!=1:raise ValueError('Invalid workspace_meta')
            if rows[0][0]!=old:raise ValueError(f'Refusing migration from schema {rows[0][0]} (expected {old})')
        print(f'Migration preview: {backend} {old} -> {new}, add 4 blank record tables; existing records unchanged')
        if not apply:return
        backup=path.with_name(path.name+'.backup-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        if backup.exists():raise ValueError('Backup target exists')
        with sqlite3.connect(path) as src,sqlite3.connect(backup) as dest:src.backup(dest)
        try:
            script=(ROOT/'migrations/sqlite-1.0.0-to-1.1.0.sql').read_text()
            with sqlite3.connect(path) as db:
                db.execute('PRAGMA foreign_keys=ON')
                db.executescript(script)
            records,errors=collect_sqlite(path);errors+=validate_records(records)
            if errors:raise ValueError('Post-migration validation failed: '+'; '.join(errors[:10]))
        except Exception:
            # Restore source to its validated pre-migration version, keeping backup intact.
            shutil.copy2(backup,path)
            raise
        print('Migration applied and validated; backup:',backup)
    else:
        if not path.is_dir():raise ValueError('CSV workspace directory not found')
        meta=path/'workspace.json'
        if not meta.is_file():raise ValueError('Missing workspace.json')
        m=json.loads(meta.read_text())
        if m.get('schema_version')!=old:raise ValueError('Expected CSV schema '+old)
        new_names=['review_findings','change_requests','change_impacts','standards_profiles']
        if any((path/(n+'.csv')).exists() for n in new_names):
            raise ValueError('New tables already exist; manual reconcile required')
        print(f'Migration preview: {backend} {old} -> {new}, add 4 blank CSVs; existing rows unchanged')
        if not apply:return
        backup=path.with_name(path.name+'.backup-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        if backup.exists():raise ValueError('Backup target exists')
        shutil.copytree(path,backup)
        try:
            for n in new_names:shutil.copy2(ROOT/'templates/csv'/f'{n}.csv',path/f'{n}.csv')
            m['schema_version']=new
            tmp=meta.with_suffix('.json.tmp');tmp.write_text(json.dumps(m,indent=2)+'\n');tmp.replace(meta)
            records,errors=collect_csv(path);errors+=validate_records(records)
            if errors:raise ValueError('Post-migration validation failed: '+'; '.join(errors[:10]))
        except Exception:
            shutil.rmtree(path);shutil.copytree(backup,path)
            raise
        print('Migration applied and validated; backup:',backup)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['init','validate','migrate']);p.add_argument('--backend',required=True,choices=['sqlite','csv']);p.add_argument('--path',required=True);p.add_argument('--workspace-id');p.add_argument('--apply',action='store_true');a=p.parse_args()
    try:
        if a.action=='init':
            if not a.workspace_id: p.error('--workspace-id required for init')
            (init_sqlite if a.backend=='sqlite' else init_csv)(a.path,a.workspace_id)
        elif a.action=='migrate':
            migrate_workspace(a.backend,a.path,apply=a.apply)
        else:
            records,errors=(collect_sqlite if a.backend=='sqlite' else collect_csv)(a.path)
            errors+=validate_records(records)
            if errors:
                for e in errors:print('ERROR:',e,file=sys.stderr)
                print('Validation failed:',len(errors),'issue(s)',file=sys.stderr);sys.exit(1)
            print('Validated',a.backend,'workspace: '+a.path,'records:',sum(map(len,records.values())))
    except (ValueError,sqlite3.Error,OSError) as e:
        print('ERROR:',e,file=sys.stderr);sys.exit(1)
if __name__=='__main__':main()
