"""Shared paths, plotting and output helpers for the research pipeline."""
from pathlib import Path
import sys,json
if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parent
DEPS=ROOT/'.research_deps'
if DEPS.exists(): sys.path.insert(0,str(DEPS))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
RESULTS=ROOT/'outputs/research'
TABLES=RESULTS/'tables'; FIGURES=RESULTS/'figures'
for p in [RESULTS,TABLES,FIGURES]: p.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'figure.dpi':130,'savefig.dpi':180,'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,'axes.titleweight':'bold','figure.facecolor':'white','axes.prop_cycle':plt.cycler(color=['#096b93','#e79636','#5f8d59','#b45c77'])})
def data(name):
 return pd.read_csv(ROOT/'data/processed'/name,parse_dates=['date_utc']).set_index('date_utc')
def table(df,name,index=False): df.to_csv(TABLES/(name+'.csv'),index=index,encoding='utf-8-sig',float_format='%.9g')
def js(obj,name): (RESULTS/(name+'.json')).write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
def figure(fig,name):
 fig.savefig(FIGURES/(name+'.png'),bbox_inches='tight'); plt.close(fig)

