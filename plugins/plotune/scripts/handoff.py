#!/usr/bin/env python3
"""Validate an explicit task packet against a local portable workspace, without writes.

This tool never launches agents and never infers permission from a packet. In hosted
RMS/Sheets workspaces, equivalent checks must use the user's connected live store.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from workspace import collect_csv, collect_sqlite, validate_records


def inspect(packet, records, workspace_id):
    issues=[]
    required=('packet_version','task_id','workspace_id','product_id','objective','scope','permissions','skill_paths','deliverables','return_contract')
    for key in required:
        if key not in packet:issues.append('Missing packet field: '+key)
    if issues:return {'valid':False,'issues':issues,'scope_checks':[]}
    if packet['packet_version']!='1.0':issues.append('Unsupported packet version')
    for field in ('task_id','workspace_id','product_id','objective'):
        if not isinstance(packet[field],str) or not packet[field].strip():issues.append('Invalid/blank '+field)
    if packet['workspace_id']!=workspace_id:issues.append('Packet belongs to a different workspace')
    products={x['product_id'] for x in records.get('products',[])}
    if packet['product_id'] not in products:issues.append('Unknown packet product')
    if not isinstance(packet['scope'],list):issues.append('scope must be an array')
    if not isinstance(packet['deliverables'],list) or not packet['deliverables']:issues.append('deliverables must be a nonempty array')
    if not isinstance(packet['skill_paths'],list) or not packet['skill_paths']:issues.append('skill_paths must be a nonempty array')
    if not isinstance(packet['return_contract'],list) or not packet['return_contract']:issues.append('return_contract must be a nonempty array')
    permissions=packet.get('permissions')
    allowed={'analyze','draft','implement','test','record_evidence'}
    if not isinstance(permissions,dict) or not isinstance(permissions.get('actions'),list) or not set(permissions.get('actions',[]))<=allowed:
        issues.append('Invalid permissions.actions')
        actions=[]
    else:actions=permissions['actions']
    if not isinstance(permissions,dict) or not isinstance(permissions.get('owned_records'),list) or not isinstance(permissions.get('owned_paths'),list):
        issues.append('Missing scoped ownership lists')
    if ('implement' in actions or 'test' in actions or 'record_evidence' in actions) and not packet['scope']:
        issues.append('Delivery/verification delegation has no revision-scoped requirements')
    tasks={x['task_id']:x for x in records.get('tasks',[])}
    matching_task=tasks.get(packet['task_id'])
    if matching_task:
        existing_session=str(matching_task.get('session_run_id') or '')
        packet_session=str(packet.get('session_run_id') or '')
        if existing_session and existing_session!=packet_session:
            issues.append('Task ID is owned by a different session; do not hijack it')
    reqs={x['requirement_id']:x for x in records.get('requirements',[])}
    baselines={x['baseline_id']:x for x in records.get('baselines',[])}
    snapshots={(x['baseline_id'],x['requirement_id'],str(x.get('requirement_revision') or '')) for x in records.get('baseline_items',[])}
    seen=set();scope_checks=[]
    if isinstance(packet['scope'],list):
        for row in packet['scope']:
            if not isinstance(row,dict) or not row.get('requirement_id') or isinstance(row.get('revision'),bool) or not isinstance(row.get('revision'),int) or row.get('revision')<1:
                issues.append('Invalid requirement scope row');continue
            rid=row['requirement_id']; rev=str(row['revision']); bid=row.get('baseline_id')
            if rid in seen:issues.append('Duplicate scoped requirement '+rid)
            seen.add(rid)
            current=reqs.get(rid)
            if not current:issues.append('Unknown scoped requirement '+rid);continue
            if current.get('product_id')!=packet['product_id']:
                issues.append('Requirement '+rid+' has a different owning product; verify applicability')
            matches_live=str(current.get('revision') or '')==rev
            matches_frozen=bool(bid and bid in baselines and baselines[bid]['status']=='Frozen' and (bid,rid,rev) in snapshots)
            if bid and not matches_frozen:issues.append('No matching frozen baseline item for '+rid+' rev '+rev+' in '+bid)
            if not matches_live and not matches_frozen:issues.append('Stale/missing requirement revision '+rid+' rev '+rev)
            scope_checks.append({'requirement_id':rid,'delegated_revision':rev,'current_revision':str(current.get('revision') or ''),
                                 'baseline_id':bid or None,'frozen_snapshot_matches':matches_frozen,
                                 'state':'LIVE_MATCH' if matches_live else 'FROZEN_SNAPSHOT_ONLY' if matches_frozen else 'CONFLICT'})
    return {'valid':not issues,'issues':issues,'task_id':packet['task_id'], 'workspace_id':workspace_id,
            'scope_checks':scope_checks,
            'warning':'Read-only preflight. Matching packet does not authorize action, launch a subagent, approve an edit, or verify a result. Re-check live revisions at integration.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--packet',required=True)
    ap.add_argument('--backend',required=True,choices=['sqlite','csv'])
    ap.add_argument('--path',required=True)
    args=ap.parse_args()
    try:
        packet=json.loads(Path(args.packet).read_text(encoding='utf-8'))
        if not isinstance(packet,dict):raise ValueError('Packet must be JSON object')
        records,errors=(collect_sqlite if args.backend=='sqlite' else collect_csv)(args.path)
        errors+=validate_records(records)
        if errors:raise ValueError('Workspace invalid: '+'; '.join(errors[:10]))
        if args.backend=='sqlite':
            with sqlite3.connect(args.path) as db:workspace_id=db.execute('SELECT workspace_id FROM workspace_meta').fetchone()[0]
        else:workspace_id=json.loads((Path(args.path)/'workspace.json').read_text())['workspace_id']
        result=inspect(packet,records,workspace_id)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if not result['valid']:raise SystemExit(2)
    except (OSError,ValueError,sqlite3.Error) as e:
        print('ERROR:',e,file=sys.stderr);raise SystemExit(1)
if __name__=='__main__':main()
