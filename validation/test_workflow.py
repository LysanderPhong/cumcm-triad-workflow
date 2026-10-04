#!/usr/bin/env python3
"""Synthetic lifecycle regressions; not a modeling or rendering benchmark."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import paper_review
import triad
class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.p=self.base/'project';self.call('start')
        (self.p/'raw/problem.txt').write_text('synthetic task')
    def tearDown(self):self.tmp.cleanup()
    def call(self,cmd,*args,ok=True,project=None):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/triad.py'),cmd,str(project or self.p),*args],capture_output=True,text=True)
        self.assertEqual(r.returncode,0 if ok else 2,r.stdout+r.stderr)
        return json.loads(r.stdout) if r.stdout else {'error':r.stderr}
    def human(self,g,status='APPROVED'):
        return self.call('record-human','--gate-id',g,'--selected','baseline','--contribution','Use median','--status',status)
    def route(self):
        for g in ('SCOPE','ROUTE'):
            h=self.human(g);self.call('close-gate','--gate-id',g)
        return h
    def execute(self):
        (self.p/'code/model.py').write_text("from pathlib import Path\nPath('results/metric.csv').write_text('metric\\n1\\n')\n")
        return self.call('run','--run-id','R1','--output','results/metric.csv','--',sys.executable,'code/model.py')
    def claim(self):return self.call('record-claim','--claim-id','C1','--text','synthetic claim','--evidence','results/metric.csv','--run-id','R1')
    def review(self,g='RESULTS',verdict='PASS',extra=()):
        flags=[]
        if g=='DELIVERY':
            for name in ('rendered_pdf','figures_tables','references','anonymity','ai_disclosure','supporting_files'):flags+=['--check',name]
        ref='paper/final.pdf' if g=='DELIVERY' else 'results/metric.csv'
        return self.call('record-review','--gate-id',g,'--verdict',verdict,'--context-id','synthetic-independent','--evidence',ref,*flags,*extra)
    def ready(self):
        h=self.route();self.execute();self.claim();r=self.review();self.call('close-gate','--gate-id','RESULTS')
        # Only tests file guard. Real PDF rendering belongs to independent delivery review.
        (self.p/'paper/final.pdf').write_bytes(b'%PDF-1.4\n'+b' '*150)
        self.review('DELIVERY');self.call('close-gate','--gate-id','DELIVERY');return h,r
    def freeze(self):return self.call('freeze','--version','v1','--confirmation','I approve this version')
    def test_complete_workflow_snapshot(self):
        self.ready();self.freeze();self.assertTrue((self.p/'releases/v1/paper/final.pdf').exists())
        self.assertTrue(self.call('status')['frozen']);self.assertEqual(self.call('validate')['status'],'VALID_RECORDS')
        manifest=self.p/'releases/v1/manifest.json'
        cmd=[sys.executable,str(ROOT/'scripts/hash_check.py'),'--manifest',str(manifest)]
        result=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('events.jsonl',{f['path'] for f in json.loads(manifest.read_text())['files']})
        (manifest.parent/'events.jsonl').write_text('tampered')
        self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,1)
        self.call('validate',ok=False)
    def test_snapshot_tampering_detected(self):
        self.ready();self.freeze();(self.p/'releases/v1/results/metric.csv').write_text('changed')
        self.call('validate',ok=False)
    def test_changed_claim_reopens_scientific_review(self):
        self.route();self.execute();self.claim();self.review();self.call('close-gate','--gate-id','RESULTS')
        self.call('record-claim','--claim-id','C1','--text','changed conclusion','--evidence','results/metric.csv','--run-id','R1')
        self.assertEqual(self.call('status')['current_gate'],'RESULTS')
        self.call('close-gate','--gate-id','RESULTS',ok=False)
    def test_missing_output_is_recorded_failure(self):
        self.call('run','--run-id','EMPTY','--output','results/missing.csv','--',sys.executable,'-c','pass',ok=False)
        self.assertIn('FAILED',(self.p/'logs/events.jsonl').read_text())
    def test_existing_output_not_credited_to_noop(self):
        (self.p/'results/old.csv').write_text('old')
        self.call('run','--run-id','NOOP','--output','results/old.csv','--',sys.executable,'-c','pass',ok=False)
    def test_latest_reject_blocks_close(self):
        self.route();self.execute();self.review();self.review(verdict='REJECT');self.call('close-gate','--gate-id','RESULTS',ok=False)
    def test_human_revocation_reopens_route(self):
        self.route();self.human('ROUTE','REJECTED');self.assertEqual(self.call('status')['current_gate'],'ROUTE');self.call('close-gate','--gate-id','ROUTE',ok=False)
    def test_changed_scope_requires_fresh_route(self):
        self.route();self.human('SCOPE');self.call('close-gate','--gate-id','SCOPE')
        self.call('close-gate','--gate-id','ROUTE',ok=False)
        self.human('ROUTE');self.call('close-gate','--gate-id','ROUTE')
    def test_fixed_failure_disappears(self):
        self.route();self.execute();f=self.call('record-failure','--description','synthetic')
        self.call('close-failure',f['failure_id'],'--repair-ref','code/model.py','--evidence','results/metric.csv')
        self.assertEqual(self.call('status')['open_failures'],[]);self.review();self.call('close-gate','--gate-id','RESULTS')
    def test_missing_repair_rejected(self):
        f=self.call('record-failure','--description','synthetic');self.call('close-failure',f['failure_id'],'--repair-ref','code/missing.py',ok=False)
    def test_draft_revision_and_approval(self):
        h=self.route();self.execute();self.claim();self.claim();r=self.review()
        self.call('approve-claim','--claim-id','C1','--decision-ref',h['event_id'],'--review-ref',r['event_id']);self.assertEqual(self.call('validate')['status'],'VALID_RECORDS')
    def test_run_cannot_impersonate_approval(self):
        self.route();r=self.execute();self.claim();self.call('approve-claim','--claim-id','C1','--decision-ref',r['event_id'],'--review-ref',r['event_id'],ok=False)
    def test_all_evidence_must_be_traced(self):
        self.route();self.execute();(self.p/'results/untraced.csv').write_text('999')
        self.call('record-claim','--claim-id','C1','--text','synthetic','--evidence','results/metric.csv','--evidence','results/untraced.csv','--run-id','R1',ok=False)
    def test_changed_output_invalidates(self):
        self.route();self.execute();self.claim();self.review();(self.p/'results/metric.csv').write_text('999')
        self.call('validate',ok=False);self.call('close-gate','--gate-id','RESULTS',ok=False)
    def test_changed_input_invalidates(self):
        self.route();self.execute();self.claim();(self.p/'raw/problem.txt').write_text('changed');self.call('validate',ok=False)
    def test_code_change_invalidates_conservatively(self):
        self.execute();self.claim();(self.p/'code/plot.py').write_text('# plot only');self.call('validate',ok=False)
    def test_imported_helper_change_and_removal_invalidates(self):
        helper=self.p/'code/helper.py';helper.write_text('value=1\n')
        (self.p/'code/model.py').write_text("from pathlib import Path\nfrom helper import value\nPath('results/helper.txt').write_text(str(value))\n")
        self.call('run','--run-id','R1','--output','results/helper.txt','--',sys.executable,'code/model.py')
        self.call('record-claim','--claim-id','C1','--text','helper value','--evidence','results/helper.txt','--run-id','R1')
        self.assertEqual(self.call('validate')['status'],'VALID_RECORDS')
        helper.write_text('value=2\n');self.call('validate',ok=False)
        helper.write_text('value=1\n');self.assertEqual(self.call('validate')['status'],'VALID_RECORDS')
        helper.unlink();self.call('validate',ok=False)
    def test_legacy_run_requires_new_execution(self):
        run=self.execute();run.pop('tracks_code',None)
        self.assertFalse(triad.current_run(self.p,run))
    def test_removed_input_during_execution_is_recorded_failure(self):
        script="from pathlib import Path;Path('raw/problem.txt').unlink();Path('results/changed.txt').write_text('1')"
        run=self.call('run','--run-id','CHANGED','--output','results/changed.txt','--',sys.executable,'-c',script,ok=False)
        self.assertEqual(run['status'],'FAILED')
        self.assertIn('inputs changed',(self.p/run['execution_log']).read_text())
    def test_late_input_preserves_human_gates(self):
        self.route();self.execute();self.review();self.call('close-gate','--gate-id','RESULTS');f=self.base/'extra.txt';f.write_text('extra');self.call('ingest',str(f))
        s=self.call('status');self.assertEqual(s['closed_gates'],['SCOPE','ROUTE']);self.assertEqual(s['current_gate'],'RESULTS')
    def test_corruption_refuses_ingest_before_copy(self):
        (self.p/'logs/events.jsonl').write_text('{bad');f=self.base/'extra.txt';f.write_text('extra');self.call('ingest',str(f),ok=False);self.assertFalse((self.p/'raw/extra.txt').exists())
    def test_no_paper_no_freeze(self):
        self.route();self.execute();self.review();self.call('close-gate','--gate-id','RESULTS');self.call('close-gate','--gate-id','DELIVERY',ok=False);self.call('freeze','--version','v1','--confirmation','yes',ok=False)
    def test_latest_delivery_reject_blocks_freeze(self):
        self.ready();self.review('DELIVERY','REJECT');self.call('freeze','--version','v1','--confirmation','yes',ok=False)
    def test_frozen_writes_refused_and_reopen(self):
        self.ready();self.freeze();self.call('record-human','--gate-id','SCOPE','--selected','x','--contribution','changed',ok=False)
        new=self.base/'next';self.call('reopen',str(new));self.assertFalse(self.call('status',project=new)['frozen']);self.assertTrue(self.call('status')['frozen'])
    def test_self_review_cannot_close(self):
        self.route();self.execute();self.review(extra=('--self-review-only',));self.call('close-gate','--gate-id','RESULTS',ok=False)
    def test_failed_and_timeout_runs_saved(self):
        for rid,script in [('FAIL','raise SystemExit(3)'),('TIME','import time;time.sleep(1)')]:
            self.call('run','--run-id',rid,'--output',f'results/{rid}.txt','--timeout','0.1','--',sys.executable,'-c',script,ok=False)
        runs=[json.loads(l) for l in (self.p/'logs/events.jsonl').read_text().splitlines() if json.loads(l)['type']=='run'];self.assertEqual([r['status'] for r in runs],['FAILED','FAILED'])
    def test_timeout_preserves_stdout_stderr(self):
        script="import sys,time;print('已完成步骤',flush=True);print('warning before timeout',file=sys.stderr,flush=True);time.sleep(10)"
        run=self.call('run','--run-id','TIME','--output','results/timeout.txt','--timeout','0.5','--',sys.executable,'-c',script,ok=False)
        log=(self.p/run['execution_log']).read_text()
        self.assertIn('已完成步骤',log.splitlines());self.assertIn('warning before timeout',log.splitlines());self.assertIn('timed out',log)
    def test_killed_lock_owner_recovery_and_live_exclusion(self):
        script="import sys,time;from pathlib import Path;import triad\nwith triad.locked(Path(sys.argv[1])):\n (Path(sys.argv[1])/'logs/holder-ready').touch()\n time.sleep(60)\n"
        child=subprocess.Popen([sys.executable,'-u','-c',script,str(self.p)],cwd=ROOT/'scripts',stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            # A bounded readiness poll avoids depending on machine speed.
            deadline=time.monotonic()+5
            while not (self.p/'logs/holder-ready').exists() and child.poll() is None and time.monotonic()<deadline:
                time.sleep(0.01)
            self.assertTrue((self.p/'logs/holder-ready').exists())
            self.call('record-failure','--description','active lock',ok=False)
            child.kill();child.communicate(timeout=5)
            self.call('record-failure','--description','after killed owner')
            self.call('record-failure','--description','subsequent write')
        finally:
            if child.poll() is None:child.kill()
            child.communicate(timeout=5)
    def test_repeat_packet_has_unique_name(self):self.assertNotEqual(self.call('review-packet')['packet'],self.call('review-packet')['packet'])
    def test_unknown_event_refused(self):
        with (self.p/'logs/events.jsonl').open('a') as f:f.write(json.dumps({'schema_version':'2.0','event_id':'bad','type':'invented'})+'\n')
        self.call('validate',ok=False)
    def test_symlink_component_refused(self):
        external=self.base/'external';external.mkdir();(external/'x.csv').write_text('x');(self.p/'results/link').symlink_to(external,target_is_directory=True)
        self.call('record-claim','--claim-id','C1','--text','x','--evidence','results/link/x.csv','--run-id','R1',ok=False)

class Presentation(unittest.TestCase):
    def test_repository_tex_template_abstract(self):
        text,warnings=paper_review.extract(ROOT/'templates/paper.tex')
        expected='简述实际任务、约束和总体思路。以下为结构占位，不是可提交的摘要。针对问题一，说明关键方法和验证过的结果；仅对关键方法或数值加粗。根据实际子问题补充摘要段落，最后说明必要的验证和结论边界。不复制参考论文的数据。'
        count=sum('\u4e00'<=c<='\u9fff' for c in expected)
        self.assertFalse(warnings);self.assertEqual(paper_review.metrics(text)['abstract_chinese_chars'],count)
        commented=text.replace('简述实际任务','% 注释文字不属于摘要\n简述实际任务')
        self.assertEqual(paper_review.metrics(commented)['abstract_chinese_chars'],count)
    def test_tex_abstract_headings_citations(self):
        m=paper_review.metrics('\\begin{abstract}简短摘要。\\end{abstract}\n\\section{问题一}\n正文\\cite{source}')
        self.assertEqual(m['abstract_chinese_chars'],4);self.assertEqual(m['headings'],1);self.assertEqual(m['citation_markers'],1)
    def test_chinese_headings_dynamic_questions_no_quota(self):
        m=paper_review.metrics('摘要\n简短摘要。\n关键词：统计\n一、问题重述\n四、问题一\n五、问题五\n')
        self.assertEqual(m['headings'],4);self.assertEqual(m['question_hits'],{'一':1,'五':1});self.assertFalse(any('摘要' in f['title'] or '篇幅' in f['title'] for f in paper_review.flags(m,None)))
        self.assertEqual(paper_review.metrics('摘要\n占比50%并保留正文。\n关键词：统计')['abstract_chinese_chars'],7)
    def test_docx_runs_joined(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'paper.docx'
            with zipfile.ZipFile(p,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>摘</w:t></w:r><w:r><w:t>要</w:t></w:r></w:p><w:p><w:r><w:t>正文。</w:t></w:r></w:p></w:body></w:document>')
            text,warnings=paper_review.extract(p);self.assertEqual(text,'摘要\n\n正文。');self.assertFalse(warnings)
    def test_style_declaration_is_not_visual_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'figure_manifest.json';p.write_text('{"fonts":{"family":"Example"}}');self.assertTrue(any(f['level']=='UNKNOWN' for f in paper_review.style_checks(p)))
    def test_spatial_3d_gradient_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'figure_manifest.json';p.write_text('{"effects":{"three_dimensional":true,"gradients":true}}');self.assertFalse(any('three_dimensional' in f['title'] or 'gradients' in f['title'] for f in paper_review.style_checks(p)))
    def test_html_rerun_new_filename_scoped_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'paper.md';p.write_text('摘要\n简短摘要。\n关键词：统计\n一、问题重述\n');out=Path(tmp)/'review.html';cmd=[sys.executable,str(ROOT/'scripts/paper_review.py'),'--paper',str(p),'--output-html',str(out)]
            subprocess.run(cmd,check=True,capture_output=True);r=subprocess.run(cmd,check=True,capture_output=True,text=True);self.assertNotEqual(json.loads(r.stdout)['output_html'],str(out));self.assertIn('const storageKey=',out.read_text())
            self.assertEqual(out.read_text().count('<b>未提供 figure_manifest.json</b>'),1)
if __name__=='__main__':unittest.main(verbosity=2)
