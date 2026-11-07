"""Offline end-to-end regression: OBC example is synthetic; no customer data.
Run: python -m unittest discover -s tests -v
"""
import csv
import json
import sqlite3
import tempfile
import unittest
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import workspace
import review
import handoff

class PortableRegression(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.db=self.home/'obc.db'
        workspace.init_sqlite(self.db,'synthetic-obc')
        with sqlite3.connect(self.db) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute("INSERT INTO products(product_id,product_name) VALUES ('OBX','Synthetic Charger')")
            db.execute("INSERT INTO requirements(requirement_id,product_id,requirement,acceptance_criteria,revision,lifecycle_status,parent_requirement_ids) VALUES ('OBX-01','OBX','Limit AC input power under defined conditions','Power stays within defined operating envelope',2,'Approved','')")
            db.execute("INSERT INTO requirements(requirement_id,product_id,requirement,acceptance_criteria,revision,lifecycle_status,parent_requirement_ids) VALUES ('OBX-02','OBX','Detect low AC voltage','Detect condition within stated threshold',1,'Approved','OBX-01')")
            db.execute("INSERT INTO requirements(requirement_id,product_id,requirement,revision,lifecycle_status,parent_requirement_ids) VALUES ('OBX-03','OBX','Recover from input fault',1,'Draft','OBX-01,OBX-02')")
            db.execute("INSERT INTO actors(actor_id,product_id,name) VALUES ('A-01','OBX','Vehicle Controller')")
            db.execute("INSERT INTO use_cases(use_case_id,product_id,title) VALUES ('UC-01','OBX','AC derating')")
            db.execute("INSERT INTO traceability(from_type,from_id,relation,to_type,to_id) VALUES ('Actor','A-01','Participates In','Use Case','UC-01')")
            db.execute("INSERT INTO traceability(from_type,from_id,relation,to_type,to_id) VALUES ('Use Case','UC-01','Motivates','Requirement','OBX-01')")
            db.execute("INSERT INTO baselines(baseline_id,product_id,status) VALUES ('BASE-1','OBX','Draft')")
            db.execute("INSERT INTO baseline_items(baseline_id,requirement_id,requirement_revision,requirement_snapshot,acceptance_criteria_snapshot) VALUES ('BASE-1','OBX-01',1,'Original behavior','Original acceptance')")
            db.execute("UPDATE baselines SET status='Frozen' WHERE baseline_id='BASE-1'")
            db.execute("INSERT INTO test_cases(test_case_id,requirement_id,requirement_revision,product_id,title) VALUES ('TEST-OLD','OBX-01',1,'OBX','Historical bench')")
            db.execute("INSERT INTO test_executions(execution_id,test_case_id,requirement_id,requirement_revision,product_id,result,coverage,evidence_summary) VALUES ('EX-OLD','TEST-OLD','OBX-01',1,'OBX','PASS','Complete','Historical test narrative')")
            db.execute("INSERT INTO test_cases(test_case_id,requirement_id,requirement_revision,product_id,title) VALUES ('TEST-NEW','OBX-01',2,'OBX','AC change followup')")
            db.execute("INSERT INTO test_cases(test_case_id,requirement_id,requirement_revision,product_id,title) VALUES ('TEST-LOW','OBX-02',1,'OBX','Voltage detection')")
            db.execute("INSERT INTO change_requests(change_id,product_id,title,status) VALUES ('CHANGE-01','OBX','Change AC behavior','Under Analysis')")
            db.execute("INSERT INTO review_findings(finding_id,product_id,record_type,record_id,record_revision,check_id,status,title) VALUES ('FIND-01','OBX','Requirement','OBX-03','1','RQ-01','Open','Acceptance missing')")
            db.execute("INSERT INTO tasks(task_id,project_id,goal,session_run_id,status) VALUES ('TASK-1','OBX','Frozen implementation','SESSION-X','Running')")
            db.execute("INSERT INTO tasks(task_id,project_id,goal,session_run_id,status) VALUES ('TASK-2','OBX','Draft requirements review','SESSION-X','Running')")
            db.commit()

    def records(self):
        records,errors=workspace.collect_sqlite(self.db)
        self.assertFalse(errors)
        self.assertFalse(workspace.validate_records(records))
        return records

    def packet(self, task='TASK-1', rev=1, baseline='BASE-1', session='SESSION-X'):
        row={'requirement_id':'OBX-01','revision':rev}
        if baseline:row['baseline_id']=baseline
        return {'packet_version':'1.0','task_id':task,'session_run_id':session,
                'workspace_id':'synthetic-obc','product_id':'OBX','objective':'Implement authorized AC derating',
                'scope':[row], 'permissions':{'actions':['implement','test'], 'owned_records':[], 'owned_paths':['firmware/ac.c']},
                'skill_paths':['skills/work-orchestration/SKILL.md','skills/traceable-delivery/SKILL.md'],
                'deliverables':['Patch and real tests'],'return_contract':['Requirement ID/revision','Evidence','Conflicts']}

    def test_evidence_history_and_coverage(self):
        r=self.records()
        old=review.coverage(r,baseline='BASE-1')
        cur=review.coverage(r,product='OBX')
        self.assertEqual(old['denominator'],1)
        self.assertIn('narrative only',old['items'][0]['status'])
        self.assertFalse(old['items'][0]['acceptance_and_maturity_confirmed'])
        self.assertEqual(next(x for x in cur['items'] if x['requirement_id']=='OBX-01')['status'],'Defined, not exercised')
        with self.assertRaisesRegex(ValueError,'Unknown baseline'):review.coverage(r,baseline='BASE-404')
        with self.assertRaisesRegex(ValueError,'Unknown product'):review.coverage(r,product='NONEXISTENT')
        with self.assertRaisesRegex(ValueError,'Unknown product'):review.quality(r,product='NONEXISTENT')

    def test_existing_project_quality_and_impact(self):
        r=self.records()
        q=review.quality(r,product='OBX')
        self.assertTrue(any(x['record_id']=='OBX-03' and 'acceptance' in x['title'].lower() for x in q['findings']))
        graph=review.impact(r,'OBX-01')
        self.assertTrue({'OBX-01','OBX-02','OBX-03'}<={x['id'] for x in graph['affected_requirements']})
        self.assertEqual(graph['seed']['revision'],'2')
        self.assertTrue(any(x['baseline_id']=='BASE-1' for x in graph['baseline_items']))
        self.assertIn('FIND-01',graph['review_findings'])

    def test_frozen_guard_and_snapshot_consistency(self):
        with sqlite3.connect(self.db) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE baseline_items SET requirement_snapshot='tamper' WHERE baseline_id='BASE-1'")
            db.rollback()
            db.execute("INSERT INTO baselines(baseline_id,product_id,status) VALUES ('BASE-2','OBX','Draft')")
            db.execute("INSERT INTO baseline_items(baseline_id,requirement_id,requirement_revision,requirement_snapshot,acceptance_criteria_snapshot) VALUES ('BASE-2','OBX-01',2,'Limit AC input power under defined conditions','Power stays within defined operating envelope')")
            db.execute("UPDATE baselines SET status='Frozen' WHERE baseline_id='BASE-2'")
            db.execute("UPDATE requirements SET requirement='Changed silently without revision' WHERE requirement_id='OBX-01'")
            db.commit()
        records,_=workspace.collect_sqlite(self.db)
        self.assertTrue(any('Frozen snapshot differs' in e for e in workspace.validate_records(records)))

    def test_two_tasks_and_stale_delegation(self):
        r=self.records()
        a=handoff.inspect(self.packet('TASK-1',1,'BASE-1'),r,'synthetic-obc')
        b=handoff.inspect(self.packet('TASK-2',2,None),r,'synthetic-obc')
        self.assertTrue(a['valid'],a)
        self.assertTrue(b['valid'],b)
        self.assertEqual(a['scope_checks'][0]['state'],'FROZEN_SNAPSHOT_ONLY')
        self.assertEqual(b['scope_checks'][0]['state'],'LIVE_MATCH')
        stale=handoff.inspect(self.packet('TASK-2',3,None),r,'synthetic-obc')
        self.assertFalse(stale['valid'])
        hijack=handoff.inspect(self.packet('TASK-1',1,'BASE-1',session='OTHER'),r,'synthetic-obc')
        self.assertFalse(hijack['valid'])
        wrong_workspace=handoff.inspect({**self.packet(), 'workspace_id':'another-company'},r,'synthetic-obc')
        self.assertFalse(wrong_workspace['valid'])

    def test_sqlite_csv_parity(self):
        rows=self.records()
        target=self.home/'csv'
        workspace.init_csv(target,'synthetic-obc')
        for name,table in workspace.TABLES.items():
            with (target/(name+'.csv')).open('w',newline='',encoding='utf-8') as out:
                writer=csv.DictWriter(out,fieldnames=table['columns']);writer.writeheader();writer.writerows(rows.get(name,[]))
        after,errors=workspace.collect_csv(target)
        self.assertFalse(errors)
        self.assertFalse(workspace.validate_records(after))
        self.assertEqual(review.quality(rows,'OBX'),review.quality(after,'OBX'))
        self.assertEqual(review.coverage(rows,'OBX'),review.coverage(after,'OBX'))
        self.assertEqual(review.impact(rows,'OBX-01'),review.impact(after,'OBX-01'))
        self.assertEqual(handoff.inspect(self.packet(),rows,'synthetic-obc'),handoff.inspect(self.packet(),after,'synthetic-obc'))

    def test_worksheets_csv_sqlite_contract(self):
        schema=json.loads((ROOT/'schema/data-model.json').read_text())
        tables=schema['tables']
        self.assertEqual(len(tables),21)
        with sqlite3.connect(':memory:') as db:
            db.executescript((ROOT/'templates/sqlite/schema.sql').read_text())
            for name, spec in tables.items():
                actual=[x[1] for x in db.execute(f'PRAGMA table_info({name})')]
                self.assertEqual(actual,spec['columns'],name)
        for name, spec in tables.items():
            with (ROOT/'templates/csv'/f'{name}.csv').open(newline='') as f:
                self.assertEqual(next(csv.reader(f)),spec['columns'],name)
        # XLSX OOXML headers (no external spreadsheet package is required for tests)
        path=ROOT/'templates/google-sheets/Plotune-Requirements-Blank.xlsx'
        ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
            'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
        rel_ns='{http://schemas.openxmlformats.org/package/2006/relationships}'
        with zipfile.ZipFile(path) as z:
            workbook_xml=ET.fromstring(z.read('xl/workbook.xml'))
            rels_xml=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
            rels={x.get('Id'):x.get('Target') for x in rels_xml.findall(rel_ns+'Relationship')}
            shared=[]
            if 'xl/sharedStrings.xml' in z.namelist():
                shared_root=ET.fromstring(z.read('xl/sharedStrings.xml'))
                shared=[''.join(t.text or '' for t in si.findall('.//m:t',ns)) for si in shared_root.findall('m:si',ns)]
            actual={}
            for sh in workbook_xml.findall('m:sheets/m:sheet',ns):
                target=rels[sh.get('{'+ns['r']+'}id')].lstrip('/')
                if not target.startswith('xl/'):target='xl/'+target
                content=ET.fromstring(z.read(target))
                row=content.find('.//m:sheetData/m:row',ns)
                values=[]
                if row is not None:
                    for cell in row.findall('m:c',ns):
                        v=cell.find('m:v',ns)
                        if cell.get('t')=='s' and v is not None:values.append(shared[int(v.text)])
                        elif cell.get('t')=='inlineStr':values.append(''.join(t.text or '' for t in cell.findall('.//m:t',ns)))
                        else:values.append(v.text if v is not None else '')
                actual[sh.get('name')]=values
        for name,spec in tables.items():
            self.assertIn(spec['sheet_name'],actual)
            self.assertEqual(actual[spec['sheet_name']],spec['columns'],name)
        self.assertTrue({'Workspace','Guide'}<=set(actual))
        self.assertEqual(len(actual),23)
        schema_packet=json.loads((ROOT/'schema/delegation-packet.schema.json').read_text())
        self.assertIn('task_id',schema_packet['required'])
        self.assertIn('permissions',schema_packet['required'])

    def test_additive_legacy_upgrade_preserves_history(self):
        legacy=self.home/'legacy.db'
        workspace.init_sqlite(legacy,'legacy-demo')
        with sqlite3.connect(legacy) as db:
            for name in ('change_impacts','review_findings','standards_profiles','change_requests'):
                db.execute('DROP TABLE '+name)
            db.execute("UPDATE workspace_meta SET schema_version='1.0.0'")
            db.execute("INSERT INTO products(product_id,product_name) VALUES ('LEG','Legacy demo')")
            db.execute("INSERT INTO requirements(requirement_id,product_id,requirement,acceptance_criteria,revision) VALUES ('LEG-001','LEG','Legacy behavior','Legacy criteria',1)")
            db.commit()
        workspace.migrate_workspace('sqlite',legacy,apply=False)
        with sqlite3.connect(legacy) as db:self.assertEqual(db.execute('SELECT schema_version FROM workspace_meta').fetchone()[0],'1.0.0')
        workspace.migrate_workspace('sqlite',legacy,apply=True)
        records,errors=workspace.collect_sqlite(legacy)
        self.assertFalse(errors)
        self.assertFalse(workspace.validate_records(records))
        self.assertEqual(records['requirements'][0]['requirement'],'Legacy behavior')
        self.assertTrue(list(self.home.glob('legacy.db.backup-*')))
        old_csv=self.home/'old-csv'
        workspace.init_csv(old_csv,'legacy-csv')
        for name in ('change_impacts','review_findings','standards_profiles','change_requests'):
            (old_csv/(name+'.csv')).unlink()
        meta=old_csv/'workspace.json';m=json.loads(meta.read_text());m['schema_version']='1.0.0';meta.write_text(json.dumps(m))
        with (old_csv/'products.csv').open('a') as stream:stream.write('LEG,Legacy CSV,,,,\n')
        workspace.migrate_workspace('csv',old_csv,apply=False)
        workspace.migrate_workspace('csv',old_csv,apply=True)
        records,errors=workspace.collect_csv(old_csv)
        self.assertFalse(errors)
        self.assertFalse(workspace.validate_records(records))
        self.assertEqual(records['products'][0]['product_name'],'Legacy CSV')
        self.assertTrue(list(self.home.glob('old-csv.backup-*')))

    def test_private_data_and_skill_contracts(self):
        forbidden=('docs.google.com/spreadsheets/d/', 'github.com/plotune/')
        for path in list((ROOT/'skills').rglob('*.md'))+list((ROOT/'docs').rglob('*.md'))+list((ROOT/'schema').rglob('*.json'))+list((ROOT/'scripts').glob('*.py')):
            text=path.read_text()
            for token in forbidden:self.assertNotIn(token,text,str(path))
        orchestration=(ROOT/'skills/work-orchestration/SKILL.md').read_text()
        self.assertIn('real',orchestration.lower())
        self.assertIn('exact requirement',orchestration.lower())
        self.assertIn('one session',orchestration.lower())

if __name__=='__main__':unittest.main()
