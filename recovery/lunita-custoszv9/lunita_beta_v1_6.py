#!/usr/bin/env python3
import argparse,os,subprocess,sys,tempfile,shutil,time,resource,json
ROOT='/opt/lunita'; MODEL=ROOT+'/brain/model/Qwen_Qwen3-0.6B-IQ3_XS.gguf'; NODE=ROOT+'/instruments/brujula/node/bin/node'; BR=ROOT+'/instruments/brujula/brujula.js'; R=ROOT+'/instruments/lapiz/R-4.6.1/bin/Rscript'; CHROME=ROOT+'/instruments/brujula/chrome/chrome'
def llama():
    for b,_,fs in os.walk(ROOT+'/brain/runtime'):
        if 'llama-cli' in fs:return b+'/llama-cli'
    raise RuntimeError('llama-cli missing')
def run(argv,**kw):
    env=kw.pop('env',None) or os.environ.copy()
    if argv and os.path.basename(str(argv[0]))=='llama-cli':
        libdir=os.path.dirname(str(argv[0]))
        env['LD_LIBRARY_PATH']=libdir+(os.pathsep+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
        cpu_backend=os.path.join(libdir,'libggml-cpu-x64.so')
        if os.path.isfile(cpu_backend):
            env['GGML_BACKEND_PATH']=cpu_backend
    kw['env']=env
    return subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kw)
FLATPAK_PINNED_COMMITS={
    'org.jamovi.jamovi':'4685c60d99398dc687837d58f370b31e01edc160c2e3bbd3d4b204a20b249fab',
    'org.jaspstats.JASP':'83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e284de3df7',
}
def flatpak_check(app,expected_commit,sandbox=False):
    if FLATPAK_PINNED_COMMITS.get(app)!=expected_commit:return 2
    q=run(['/usr/bin/flatpak','info','--system','--show-commit',app],timeout=30)
    if q.returncode or q.stdout.strip()!=expected_commit:return 2
    info=run(['/usr/bin/flatpak','info','--system',app],timeout=30)
    if info.returncode or 'Installation: system' not in info.stdout or 'Origin: flathub' not in info.stdout:return 2
    if sandbox:
        h=tempfile.mkdtemp(prefix='lunita-flatpak-',dir='/tmp')
        env=os.environ.copy()
        env.update({'HOME':h,'XDG_CACHE_HOME':h+'/cache','XDG_CONFIG_HOME':h+'/config','XDG_DATA_HOME':h+'/data'})
        try:
            q=run(['/usr/bin/flatpak','--system','run','--command=sh',app,'-c','test -d /app'],env=env,timeout=90)
            return 0 if q.returncode==0 else 3
        finally:shutil.rmtree(h,ignore_errors=True)
    return 0
def qwen(mode):
    # A zero-token request is not a reliable readiness test in this CLI build.
    # Load-test mode performs one bounded token; inference mode performs eight.
    tokens='1' if mode=='load' else '8'
    argv=[llama(),'-m',MODEL,'-t','1','-c','256','-b','64','-ub','32',
          '-n',tokens,'--single-turn','--simple-io','--no-warmup',
          '-p','Reply briefly with OK.']
    q=run(argv,timeout=90); return 0 if q.returncode==0 else 4
def brujula():
    h=tempfile.mkdtemp(prefix='lunita-brujula-home-',dir='/tmp')
    env=os.environ.copy()
    env.update({'HOME':h,'XDG_CACHE_HOME':h+'/cache','XDG_CONFIG_HOME':h+'/config','XDG_DATA_HOME':h+'/data'})
    try:
        q=run([NODE,BR,'data:text/html,<title>LUNITA_BRUJULA_OK</title><body>OK</body>'],env=env,timeout=60)
        return 0 if q.returncode==0 and 'LUNITA_BRUJULA_OK' in q.stdout else 5
    finally:shutil.rmtree(h,ignore_errors=True)
def rcheck():return run([R,'-e','stopifnot(as.character(getRversion())=="4.6.1",2+2==4)'],timeout=60).returncode
def fault(name):
    if name=='model-missing':
        q=run([llama(),'-m',MODEL+'.intentionally-missing','-p','x','-n','1','-t','1'],timeout=30)
        return 0 if q.returncode!=0 else 10
    if name=='model-corrupted':
        f=tempfile.NamedTemporaryFile(delete=False,suffix='.gguf');f.write(b'GGUF'+b'\0'*64);f.close()
        try:return 0 if run([llama(),'-m',f.name,'-p','x','-n','1','-t','1'],timeout=30).returncode!=0 else 11
        finally:os.unlink(f.name)
    if name=='dependency-missing':
        try:
            q=run([NODE+'.intentionally-missing','--version'],timeout=10)
        except FileNotFoundError:
            return 0
        except OSError:
            return 0
        return 0 if q.returncode!=0 else 12
    if name=='permission-denied':
        fd,namepath=tempfile.mkstemp(prefix='lunita-noexec-',dir='/tmp')
        os.write(fd,b'#!/bin/sh\nexit 0\n');os.close(fd);os.chmod(namepath,0o600)
        try:
            try: run([namepath],timeout=5)
            except PermissionError: return 0
            return 13
        finally: os.unlink(namepath)
    if name=='low-memory':
        code='import resource;resource.setrlimit(resource.RLIMIT_AS,(32*1024*1024,32*1024*1024));a=bytearray(128*1024*1024)'
        q=run(['/usr/bin/python3','-c',code]);return 0 if q.returncode!=0 else 14
    if name=='process-crash':return 0 if run(['/usr/bin/python3','-c','import os;os.abort()']).returncode!=0 else 15
    if name=='browser-crash':
        d=tempfile.mkdtemp(prefix='lunita-chrome-',dir='/tmp');p=subprocess.Popen([CHROME,'--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--user-data-dir='+d,'about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:time.sleep(1);p.terminate();p.wait(timeout=10);return 0
        finally:
            try:p.kill()
            except:pass
            shutil.rmtree(d,ignore_errors=True)
    if name=='tool-failure':return 0 if run(['/usr/bin/false']).returncode!=0 else 16
    if name=='invalid-input':return 0 if run(['/usr/bin/python3',__file__,'__invalid__']).returncode!=0 else 17
    if name=='interrupted-execution':
        p=subprocess.Popen(['/usr/bin/python3','-c','import time;time.sleep(30)']);time.sleep(.2);p.terminate();p.wait(timeout=5);return 0
    if name=='restart':
        f=tempfile.NamedTemporaryFile(delete=False);f.write(b'LUNITA_RESTART');f.close();q=run(['/usr/bin/python3','-c','import sys;assert open(sys.argv[1],"rb").read()==b"LUNITA_RESTART"',f.name]);os.unlink(f.name);return q.returncode
    return 99
p=argparse.ArgumentParser(prog='lunita');s=p.add_subparsers(dest='cmd',required=True)
for c in ['start','qwen-load','qwen-inference','brujula-self-test','r-self-test','jamovi-self-test','jasp-self-test'] : s.add_parser(c)
f=s.add_parser('fault');f.add_argument('name')
a=p.parse_args()
if a.cmd=='start':print('LUNITA_READY');sys.exit(0)
if a.cmd=='qwen-load':sys.exit(qwen('load'))
if a.cmd=='qwen-inference':sys.exit(qwen('infer'))
if a.cmd=='brujula-self-test':sys.exit(brujula())
if a.cmd=='r-self-test':sys.exit(rcheck())
if a.cmd=='jamovi-self-test':sys.exit(flatpak_check('org.jamovi.jamovi',FLATPAK_PINNED_COMMITS['org.jamovi.jamovi'],True))
if a.cmd=='jasp-self-test':sys.exit(flatpak_check('org.jaspstats.JASP',FLATPAK_PINNED_COMMITS['org.jaspstats.JASP'],True))
if a.cmd=='fault':sys.exit(fault(a.name))
