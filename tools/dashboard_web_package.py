"""Smaller web transport of the same public dashboard, with lazy replay bytes."""
import base64
import gzip
import hashlib
import json
import re

SCRIPT = re.compile(r'<script>(.*?)</script>', re.S)
ARCHIVE = re.compile(r'const HISTORY_ARCHIVE_GZIP_B64="([A-Za-z0-9+/=]+)";')
BOOT = '''/* ORBIT WEB TRANSPORT */
const ORBIT_APP_GZIP_B64=__PROGRAM__;
(async()=>{
 try{
  if(typeof DecompressionStream==='undefined')throw Error('Hãy dùng Chrome, Edge hoặc Safari phiên bản mới để mở dashboard.');
  const response=await fetch('data:application/gzip;base64,'+ORBIT_APP_GZIP_B64);
  const program=await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).text();
  const script=document.createElement('script');script.textContent=program;document.body.appendChild(script);
 }catch(error){
  const status=document.getElementById('bootStatus');if(status){status.hidden=false;status.textContent='Chưa mở được dashboard: '+error.message;const retry=document.createElement('button');retry.textContent='Tải lại';retry.onclick=()=>location.reload();status.appendChild(retry);}
 }
})();'''


def package_dashboard(raw):
    html=raw.decode('utf-8')
    matches=list(SCRIPT.finditer(html))
    if len(matches)!=1:
        raise ValueError('Expected the single verified dashboard program')
    script=matches[0]
    archive=ARCHIVE.search(script[1])
    if archive is None:
        raise ValueError('Missing embedded replay archive')
    data=base64.b64decode(archive[1],validate=True)
    filename='replay-'+hashlib.sha256(data).hexdigest()[:16]+'.bin'
    replacement='const HISTORY_ARCHIVE_GZIP_B64="";\nconst HISTORY_ARCHIVE_URL='+json.dumps(filename)+';'
    program=script[1][:archive.start()]+replacement+script[1][archive.end():]
    encoded=base64.b64encode(gzip.compress(program.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
    boot=BOOT.replace('__PROGRAM__',json.dumps(encoded))
    packed=html[:script.start(1)]+boot+html[script.end(1):]
    return {'dashboard/index.html':packed.encode('utf-8'),'dashboard/'+filename:data}


def unpack_program(packed,assets):
    """Recover exact original program bytes for publication verification."""
    code=SCRIPT.search(packed.decode('utf-8'))[1]
    encoded=json.loads(re.search(r'const ORBIT_APP_GZIP_B64=("[A-Za-z0-9+/=]+");',code)[1])
    program=gzip.decompress(base64.b64decode(encoded,validate=True)).decode('utf-8')
    archive=re.search(r'const HISTORY_ARCHIVE_GZIP_B64="";\nconst HISTORY_ARCHIVE_URL=("[^"]+");',program)
    name='dashboard/'+json.loads(archive[1])
    data=assets[name]
    original='const HISTORY_ARCHIVE_GZIP_B64='+json.dumps(base64.b64encode(data).decode('ascii'))+';'
    return program[:archive.start()]+original+program[archive.end():]
