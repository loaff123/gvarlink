"""Install the built wheel into an isolated venv and run outside the checkout."""
import json, os, pathlib, subprocess, sys, tempfile, venv
ROOT=pathlib.Path(__file__).resolve().parents[1]
wheel=next((ROOT/'dist').glob('gvarlink-*.whl'))
with tempfile.TemporaryDirectory(prefix='gvarlink-wheel-') as tmp:
    root=pathlib.Path(tmp);venv.EnvBuilder(with_pip=True,system_site_packages=False).create(root/'venv')
    python=root/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'requirements-validation.txt')],cwd=root,env=env,check=True,capture_output=True)
    subprocess.run([str(python),'-m','pip','install','--no-deps',str(wheel)],cwd=root,env=env,check=True,capture_output=True)
    check=subprocess.run([str(python),'-c',"import gvarlink; print(gvarlink.__file__)"],cwd=root,env=env,check=True,text=True,capture_output=True)
    assert str(ROOT/'src') not in check.stdout,check.stdout
    demo=subprocess.run([str(python),'-m','gvarlink','demo',str(root/'demo')],cwd=root,env=env,check=True,text=True,capture_output=True,timeout=45)
    result=json.loads(demo.stdout);assert result['shared_contrast_variance']==0 and result['independent_equal_contrast_variance']==8
    print(json.dumps({'wheel':wheel.name,'installed_import':check.stdout.strip(),'outside_checkout':True,'demo':result},sort_keys=True))
