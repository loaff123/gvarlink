import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
import gvarlink as gl

ROOT=Path(__file__).resolve().parents[1]
ENV={**os.environ,'PYTHONPATH':str(ROOT/'src')}


def run(*args):return subprocess.run([sys.executable,'-m','gvarlink',*map(str,args)],env=ENV,capture_output=True,text=True,timeout=45)


def test_demo_cli_then_verify(tmp_path):
    out=tmp_path/'demo';proc=run('demo',out)
    assert proc.returncode==0,proc.stderr
    report=json.loads(proc.stdout)
    assert report['shared_contrast_variance']==0
    assert report['independent_equal_contrast_variance']==8
    assert len(set(report['worker_pids']))==3
    assert json.loads(run('inspect',out/'branch-1.gvl').stdout)['integrity']=='verified'
    check=run('verify',out/'branch-1.gvl',out/'branch-2.gvl');assert check.returncode==0,check.stderr
    assert json.loads(check.stdout)['files']==2
    assert run('demo',out).returncode!=0


def test_cli_bad_input_has_nonzero_concise_error(tmp_path):
    p=tmp_path/'bad';p.write_bytes(b'bad')
    proc=run('inspect',p)
    assert proc.returncode==2 and 'error:' in proc.stderr and 'Traceback' not in proc.stderr


def test_conservative_rebin_example(tmp_path):
    proc=subprocess.run([sys.executable,str(ROOT/'examples'/'rebin_counts.py'),str(tmp_path/'rebin')],env=ENV,text=True,capture_output=True,timeout=30)
    assert proc.returncode==0,proc.stderr
    result=json.loads(proc.stdout)
    assert result['input_integral']==result['output_integral']==77
    assert result['integral_variance_before']==result['integral_variance_after']==26.75
    assert result['coverage']==[1.0,1.0,0.0,1.0]
    assert result['zero_coverage_is_missing_support'] is True
