"""Phase 1: frozen-data audit, descriptive statistics, tails and regime comparisons."""
from research_common import *
from scipy.stats import jarque_bera

def main():
 d=data('daily_research_latest.csv')
 cols=['btc_usd_log_return','eth_usd_log_return','vix_change','broad_usd_log_return','us2y_change_bps','us10y_change_bps','fed_funds_change_bps','sp500_log_return','gold_futures_log_return','oil_wti_log_return','nfci']
 rows=[]
 for regime,frame in [('full',d),('pre2020',d.loc[:'2019-12-31']),('post2020',d.loc['2020-01-01':])]:
  for col in cols:
   s=frame[col].dropna(); jb=jarque_bera(s)
   rows.append(dict(regime=regime,variable=col,n=len(s),mean=s.mean(),std=s.std(),median=s.median(),min=s.min(),q01=s.quantile(.01),q05=s.quantile(.05),q95=s.quantile(.95),q99=s.quantile(.99),max=s.max(),skew=s.skew(),excess_kurtosis=s.kurt(),jb_stat=jb.statistic,jb_pvalue=jb.pvalue))
 desc=pd.DataFrame(rows); table(desc,'descriptive_statistics')
 missing=pd.DataFrame({'variable':d.columns,'n_missing':d.isna().sum().values,'missing_fraction':d.isna().mean().values})
 table(missing,'missingness')
 extremes=[]
 for asset in ['btc','eth']:
  s=d[asset+'_usd_log_return'].dropna(); e=s.abs().nlargest(10).index
  for date in e: extremes.append({'asset':asset,'date_utc':date,'log_return':s.loc[date],'simple_return':np.expm1(s.loc[date])})
 table(pd.DataFrame(extremes),'crypto_extreme_returns')
 # Pairwise correlations are descriptive: n varies by pair; no significance claims.
 correlations=[]
 for regime,frame in [('full',d),('pre2020',d.loc[:'2019-12-31']),('post2020',d.loc['2020-01-01':])]:
  for y in ['btc_usd_log_return','eth_usd_log_return']:
   for x in cols[2:]:
    pair=frame[[y,x]].dropna()
    correlations.append(dict(regime=regime,asset=y.split('_')[0],variable=x,n=len(pair),pearson=pair.corr().iloc[0,1],spearman=pair.corr(method='spearman').iloc[0,1]))
 corr=pd.DataFrame(correlations); table(corr,'descriptive_correlations')
 discrepancies=pd.read_csv(ROOT/'data/processed/sp500_source_discrepancies.csv',parse_dates=['date_utc'])
 # An uncertain price affects its own return and the next observed S&P return.
 sp_dates=d.sp500.dropna().index; bad=set()
 for date in discrepancies.date_utc:
  bad.add(date); loc=sp_dates.get_indexer([date])[0]
  if 0<=loc<len(sp_dates)-1: bad.add(sp_dates[loc+1])
 robustness=[]
 for a in ['btc','eth']:
  pair=d[[a+'_usd_log_return','sp500_log_return']].dropna()
  for label,p in [('all_source_dates',pair),('exclude_discrepant_and_next_session',pair.loc[~pair.index.isin(bad)])]:
   robustness.append(dict(asset=a,sample=label,n=len(p),pearson=p.corr().iloc[0,1]))
 table(pd.DataFrame(robustness),'sp500_discrepancy_sensitivity')
 fig,ax=plt.subplots(3,1,figsize=(12,9),sharex=True)
 for a in ['btc','eth']: ax[0].plot(d.index,d[a+'_usd'],label=a.upper(),linewidth=.9)
 ax[0].set_yscale('log'); ax[0].set_ylabel('USD, log scale'); ax[0].legend(); ax[0].set_title('Crypto and global financial conditions | frozen through 15 Oct 2026')
 ax[1].plot(d.index,d.vix,label='VIX',linewidth=.8); ax[1].set_ylabel('VIX points'); ax[1].legend()
 ax[2].plot(d.index,d.us2y,label='US 2Y',linewidth=.9); ax[2].plot(d.index,d.us10y,label='US 10Y',linewidth=.9); ax[2].set_ylabel('Yield (%)'); ax[2].legend()
 for a in ax: a.axvline(pd.Timestamp('2020-01-01'),color='#707070',linestyle='--',linewidth=.8)
 fig.tight_layout(); figure(fig,'eda_history')
 fig,axes=plt.subplots(2,2,figsize=(12,7))
 for j,a in enumerate(['btc','eth']):
  for reg,mask in [('pre2020',d.index<'2020-01-01'),('post2020',d.index>='2020-01-01')]:
   s=d.loc[mask,a+'_usd_log_return'].dropna()*100
   axes[0,j].hist(s,bins=90,range=(-25,25),density=True,alpha=.5,label=reg)
  axes[0,j].set_title(a.upper()+' daily log returns'); axes[0,j].set_xlabel('Percent; display clipped to [-25,25], statistics use full tails'); axes[0,j].legend()
  axes[1,j].plot(d.index,d[a+'_vol30_annualized']*100,linewidth=.8); axes[1,j].set_ylabel('Annualized RMS volatility (%)'); axes[1,j].set_title('Backward-looking 30-day volatility proxy')
 fig.tight_layout(); figure(fig,'eda_returns_volatility')
 mat=d[cols[:6]].corr(); fig,ax=plt.subplots(figsize=(8,6)); im=ax.imshow(mat,vmin=-1,vmax=1,cmap='RdBu_r'); ax.grid(False)
 labels=['BTC return','ETH return','VIX change','Broad USD return','2Y change','10Y change']
 ax.set_xticks(range(6),labels,rotation=35,ha='right'); ax.set_yticks(range(6),labels)
 for i in range(6):
  for j in range(6): ax.text(j,i,f'{mat.iloc[i,j]:.2f}',ha='center',va='center',color='white' if abs(mat.iloc[i,j])>.6 else '#222')
 fig.colorbar(im,ax=ax,label='Pairwise Pearson correlation'); ax.set_title('Descriptive daily correlations | unequal pairwise samples'); fig.tight_layout(); figure(fig,'eda_correlations')
 checks={'unique_dates':d.index.is_unique,'ordered_dates':d.index.is_monotonic_increasing,'full_4671_days':len(d)==4671,'no_infinities':not np.isinf(d.select_dtypes('number')).any().any(),'no_move':not any('move' in c.lower() for c in d.columns),'btc_no_missing':d.btc_usd_log_return.notna().all(),'negative_wti_retained':(d.oil_wti<0).any()}
 assert all(checks.values()),checks
 js({'checks':{k:bool(v) for k,v in checks.items()},'sp500_affected_return_dates':sorted(str(x.date()) for x in bad),'test_use':'Full-sample descriptive EDA belongs to historical analysis; forecasting features and splits remain fixed, not selected from test performance.'},'eda_audit')
 print(desc[desc.variable.isin(['btc_usd_log_return','eth_usd_log_return'])].to_string(index=False))
 # A runnable notebook uses the same script and saved tables; no fabricated cell outputs.
 import nbformat
 nb=nbformat.v4.new_notebook(); nb.cells=[nbformat.v4.new_markdown_cell('# Chủ đề 9: EDA\nSnapshot 16/10/2026. Số liệu lịch sử ex post; không diễn giải tương quan thành nhân quả. Không dùng EDA để chọn feature theo test.'),nbformat.v4.new_code_cell("from pathlib import Path\nimport os, sys\nroot=Path.cwd() if Path('research_eda.py').exists() else Path.cwd().parent\nos.chdir(root)\nsys.path.insert(0,str(root))\nfrom research_eda import main\nmain()"),nbformat.v4.new_code_cell("import pandas as pd\npd.read_csv('outputs/research/tables/descriptive_statistics.csv')"),nbformat.v4.new_markdown_cell('## Giá và điều kiện tài chính\n![History](../outputs/research/figures/eda_history.png)'),nbformat.v4.new_markdown_cell('## Phân phối return và volatility\n![Returns](../outputs/research/figures/eda_returns_volatility.png)'),nbformat.v4.new_code_cell("pd.read_csv('outputs/research/tables/sp500_discrepancy_sensitivity.csv')")]
 (ROOT/'notebooks').mkdir(exist_ok=True); nbformat.write(nb,ROOT/'notebooks/01_eda.ipynb')
 return desc
if __name__=='__main__': main()
