"""ALFRED public bulk exports, real-time-period format, without an API key."""
from pathlib import Path
import requests,re,datetime,json,hashlib,time,subprocess,urllib.parse,zipfile,io
import pandas as pd
ROOT=Path(__file__).resolve().parent
RAW=ROOT/'data'/'raw'
def download(series):
 url=f'https://alfred.stlouisfed.org/series/downloaddata?seid={series}'
 form_path=RAW/f'{series}_alfred_form.html'
 subprocess.run(['curl.exe','-f','-sS','-L','--max-time','35','-o',str(form_path),url],check=True,timeout=40)
 html=form_path.read_text(encoding='utf-8')
 # Use all vintages, including earlier vintages that can cover our sample start.
 dates=sorted(set(re.findall(r'<option value="(\d{4}-\d{2}-\d{2})"',html)))
 dates=[d for d in dates if '2013-12-01'<=d<='2026-10-15']
 last_obs=re.search(r'id="form_obs_end_date"[^>]*value="([^"]+)"',html).group(1)
 fields=[('form[units]','lin'),('form[obs_start_date]','2013-12-01'),('form[obs_end_date]',min(last_obs,'2026-10-15')),
         ('form[entered_vintage_dates]',''),('form[file_type]','1'),('form[file_format]','csv'),('form[download_data]','')]
 for tag in re.findall(r'<input\b[^>]*>',html):
  if 'type="hidden"' in tag:
   n=re.search(r'name="([^"]+)"',tag); v=re.search(r'value="([^"]*)"',tag)
   if n: fields.append((n.group(1),v.group(1) if v else ''))
 print(series,'vintage dates',len(dates),flush=True)
 p=RAW/f'{series}_alfred_realtime.zip'
 tables=[]; readme=b''
 for i in range(0,len(dates),400):
  part=RAW/f'{series}_alfred_part{i//400:02d}.zip'
  if not part.exists() or part.read_bytes()[:2]!=b'PK':
   body_path=RAW/f'{series}_alfred_request.txt'
   payload=fields+[('form[selected_vintage_dates][]',d) for d in dates[i:i+400]]
   body_path.write_text(urllib.parse.urlencode(payload),encoding='ascii')
   subprocess.run(['curl.exe','-f','-sS','-L','--max-time','90','--data-binary','@'+str(body_path),'-o',str(part),url],check=True,timeout=95)
  content=part.read_bytes()
  if content[:2]!=b'PK':
   part.replace(RAW/f'{series}_alfred_error.html')
   raise ValueError(f'Expected ZIP; got {len(content)} bytes')
  z=zipfile.ZipFile(io.BytesIO(content)); readme=z.read('README.txt')
  tables.append(pd.read_csv(io.BytesIO(z.read('obs._by_real-time_period.csv')),dtype=str))
  print(series,'part',i//400,'rows',len(tables[-1]),flush=True)
 table=pd.concat(tables,ignore_index=True).drop_duplicates()
 assert pd.to_datetime(table.realtime_start_date).min()<pd.Timestamp('2020-01-01'),'Missing historical coverage'
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('README.txt',readme+b'\nMerged and deduplicated public ALFRED real-time-period exports; see original part ZIPs.\n')
  z.writestr('obs._by_real-time_period.csv',table.to_csv(index=False))
 content=p.read_bytes()
 log_path=ROOT/'data'/'source_log.json'
 old=json.loads(log_path.read_text())
 rec={'file':p.name,'url':url,'method':'POST public download form','output_type':'Observations by Real-Time Period','vintages_selected':len(dates),'status':'ok','retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
 old=[x for x in old if x['file']!=p.name]+[rec]; log_path.write_text(json.dumps(old,indent=2),encoding='utf-8')
 print(series,'OK',len(content),flush=True)
if __name__=='__main__':
 for series in ['NFCI','DTWEXBGS','DFF','DGS2','DGS10','DCOILWTICO']:
  existing=RAW/f'{series}_alfred_realtime.zip'
  if existing.exists() and existing.read_bytes()[:2]==b'PK':
   z=zipfile.ZipFile(existing)
   if b'Merged and deduplicated' in z.read('README.txt'): continue
  for attempt in range(3):
   try: download(series); break
   except Exception as e: print(series,'attempt',attempt+1,str(e),flush=True); time.sleep(2)
