"""Approved extension: weekday and elapsed-session controls for the existing VAR.

Read the frozen session panels. Preserve baseline, LP, events and forecast results.
Keep lag search 0..10 and minimum fitted lag 1, with BIC/AIC as in baseline.
Do not select specifications or add lags in order to pass whiteness tests.
"""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
 os.environ.setdefault(key,'2')
from research_common import *
import hashlib,html,zipfile
from statsmodels.tsa.api import VAR
from statsmodels.stats.diagnostic import acorr_ljungbox

OUT=RESULTS/'var_calendar_extension'
NAMES=['vix_change','usd_return_pct','us2y_change_bps','us10y_change_bps','crypto_return_pct']
SHOCKS={'vix_change':5.,'usd_return_pct':1.,'us2y_change_bps':10.,'us10y_change_bps':10.}
SPECS=['baseline','weekday','gap','weekday_gap']

def save(frame,name):
 frame.to_csv(OUT/(name+'.csv'),index=False,encoding='utf-8-sig',float_format='%.12g')

def controls(panel):
 x=pd.DataFrame(index=panel.index)
 for weekday,label in [(1,'tuesday'),(2,'wednesday'),(3,'thursday'),(4,'friday')]:
  x[label]=(panel.index.dayofweek==weekday).astype(float)
 x['extra_calendar_days']=panel.elapsed_calendar_days-1.
 return x

def external_input_hashes():
 files=list((ROOT/'data').rglob('*'))+list((RESULTS/'tables').rglob('*'))+list((RESULTS/'figures').rglob('*'))+list((RESULTS/'dashboard').rglob('*'))
 files += [RESULTS/'report.html',RESULTS/'report.md',ROOT/'notebooks/01_eda.ipynb']
 return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}

def fit_model(y,x,lag):
 return VAR(y.reset_index(drop=True),exog=None if x is None else x.reset_index(drop=True)).fit(lag)

def irf_records(res,asset,regime,spec,criterion):
 irf=res.irf(30); se=irf.stderr(orth=True); chol=np.linalg.cholesky(np.asarray(res.sigma_u)); rows=[]
 for shock,scale in SHOCKS.items():
  j=NAMES.index(shock); factor=scale/chol[j,j]
  for h in range(31):
   b=float(irf.orth_irfs[h,4,j]*factor); s=float(se[h,4,j]*abs(factor))
   rows.append(dict(asset=asset,regime=regime,specification=spec,criterion=criterion,lag=res.k_ar,shock=shock,shock_size=scale,horizon_sessions=h,response_pct=b,se=s,lower95=b-1.96*s,upper95=b+1.96*s))
 return rows

def main():
 OUT.mkdir(exist_ok=True)
 before=external_input_hashes()
 diagnostics=[]; irfs=[]; selections=[]; coefficients=[]; residuals=[]; autocorr=[]; ranks=[]; checks={}
 old=pd.read_csv(TABLES/'var_diagnostics.csv')
 old_robust=pd.read_csv(TABLES/'var_robustness_diagnostics.csv')
 for asset in ['btc','eth']:
  panel=data(asset+'_econometric_sessions.csv')
  assert set(panel.index.dayofweek).issubset(set(range(5)))
  xall=controls(panel)
  audit=xall.copy(); audit.insert(0,'date_utc',panel.index); audit.insert(1,'elapsed_calendar_days',panel.elapsed_calendar_days.values)
  save(audit,asset+'_calendar_controls')
  # Validate every retained interval with its source prices, ignoring only the first saved interval.
  raw=data('daily_research_latest.csv')
  exact=100*np.log(raw[asset+'_usd'].reindex(panel.index)).diff().iloc[1:]
  checks[asset+'_same_return_intervals']=bool(np.allclose(exact,panel.crypto_return_pct.iloc[1:],atol=1e-7))
  checks[asset+'_gap_matches_dates']=bool(np.array_equal(panel.index.to_series().diff().dt.days.iloc[1:],panel.elapsed_calendar_days.iloc[1:]))
  for regime,g in [('full',panel),('pre2020',panel.loc[:'2019-12-31']),('post2020',panel.loc['2020-01-01':])]:
   y=g[NAMES]; x=xall.loc[g.index]; base_ref=old[(old.asset==asset)&(old.regime==regime)].iloc[0]
   for spec in SPECS:
    exog=None if spec=='baseline' else x.drop(columns='extra_calendar_days') if spec=='weekday' else x[['extra_calendar_days']] if spec=='gap' else x
    design=np.ones((len(g),1)) if exog is None else np.column_stack([np.ones(len(g)),exog.to_numpy()])
    rank=int(np.linalg.matrix_rank(design)); assert rank==design.shape[1],(asset,regime,spec,'collinear controls')
    ranks.append(dict(asset=asset,regime=regime,specification=spec,n_input=len(g),n_deterministic_columns=design.shape[1],rank=rank))
    selection=VAR(y.reset_index(drop=True),exog=None if exog is None else exog.reset_index(drop=True)).select_order(10)
    for criterion in ['bic','aic']:
     selected=int(selection.selected_orders[criterion]); lag=max(1,selected)
     for candidate,value in enumerate(selection.ics[criterion]):
      selections.append(dict(asset=asset,regime=regime,specification=spec,criterion=criterion,candidate_lag=candidate,ic_value=value,raw_selected_lag=selected,fitted_lag=lag))
     fit=fit_model(y,exog,lag)
     white={h:fit.test_whiteness(nlags=h,adjusted=True) for h in [max(10,lag+1),20,30]}
     row=dict(asset=asset,regime=regime,specification=spec,criterion=criterion,lag=lag,nobs=int(fit.nobs),n_parameters=int(fit.params.size),stable=bool(fit.is_stable()),max_companion_eigenvalue=float(np.max(1/np.abs(fit.roots))),whiteness_p20=float(white[20].pvalue),whiteness_stat20=float(white[20].test_statistic),whiteness_p30=float(white[30].pvalue),same_lag_as_baseline=bool(lag==int(base_ref[criterion+'_lag'])))
     diagnostics.append(row); irfs.extend(irf_records(fit,asset,regime,spec,criterion))
     if spec=='baseline':
      ref=float(base_ref.whiteness_p) if criterion=='bic' else float(old_robust[(old_robust.asset==asset)&(old_robust.regime==regime)&(old_robust.specification=='aic_lag')].whiteness_p.iloc[0])
      checks[f'{asset}_{regime}_{criterion}_baseline_reproduced']=bool(np.isclose(row['whiteness_p20'],ref,rtol=2e-5,atol=1e-12))
     if exog is not None:
      for term in exog.columns:
       for equation in NAMES:
        coefficients.append(dict(asset=asset,regime=regime,specification=spec,criterion=criterion,term=term,equation=equation,beta=fit.params.loc[term,equation],se=fit.stderr.loc[term,equation],pvalue_asymptotic=fit.pvalues.loc[term,equation]))
     # Residual diagnostics for the complete calendar specification and its matched baseline.
     if spec in ['baseline','weekday_gap']:
      u=fit.resid
      for eq in NAMES:
       test=acorr_ljungbox(u[eq],lags=[20],model_df=lag,return_df=True)
       residuals.append(dict(asset=asset,regime=regime,specification=spec,criterion=criterion,equation=eq,own_autocorr_ljungbox_p20=float(test.lb_pvalue.iloc[0]),note='Univariate own-serial diagnostic; not a replacement for joint cross-correlation Portmanteau.'))
      for k in range(1,21):
       for j,eq in enumerate(NAMES):
        a=np.asarray(u)[k:]; b=np.asarray(u)[:-k]
        for l,lagged_eq in enumerate(NAMES):
         corr=float(np.corrcoef(a[:,j],b[:,l])[0,1])
         autocorr.append(dict(asset=asset,regime=regime,specification=spec,criterion=criterion,lag_sessions=k,current_equation=eq,lagged_equation=lagged_eq,residual_correlation=corr))
   print('Completed calendar VAR:',asset,regime,flush=True)
 diag=pd.DataFrame(diagnostics); irf=pd.DataFrame(irfs)
 base=diag[diag.specification=='baseline'].set_index(['asset','regime','criterion'])
 compare=diag[diag.specification=='weekday_gap'].copy()
 compare['baseline_whiteness_p20']=[base.loc[(r.asset,r.regime,r.criterion),'whiteness_p20'] for r in compare.itertuples()]
 compare['baseline_lag']=[base.loc[(r.asset,r.regime,r.criterion),'lag'] for r in compare.itertuples()]
 compare['baseline_nobs']=[base.loc[(r.asset,r.regime,r.criterion),'nobs'] for r in compare.itertuples()]
 compare['reject_whiteness_5pct']=compare.whiteness_p20<.05
 # Keep comparisons keyed on both IC and regime. No mixing of AIC/BIC results.
 ref=irf[irf.specification=='baseline'].drop(columns=['specification']).rename(columns={'response_pct':'baseline_response_pct','lag':'baseline_lag'})
 comp_irf=irf[irf.specification=='weekday_gap'].merge(ref[['asset','regime','criterion','shock','horizon_sessions','baseline_response_pct','baseline_lag']],on=['asset','regime','criterion','shock','horizon_sessions'],validate='one_to_one')
 comp_irf['response_difference_pp']=comp_irf.response_pct-comp_irf.baseline_response_pct
 checks['all_calendar_models_stable']=bool(diag.stable.all())
 checks['irf_rows_finite']=bool(np.isfinite(irf[['response_pct','se','lower95','upper95']].to_numpy()).all())
 checks['matched_irf_rows']=len(comp_irf)==2*3*2*4*31
 checks['no_baseline_or_forecasting_mutation']=before==external_input_hashes()
 assert all(checks.values()),checks
 for frame,name in [(diag,'diagnostics'),(compare,'baseline_comparison'),(irf,'impulse_responses'),(comp_irf,'irf_comparison'),(pd.DataFrame(selections),'lag_selection'),(pd.DataFrame(coefficients),'calendar_coefficients'),(pd.DataFrame(residuals),'residual_own_serial_tests'),(pd.DataFrame(autocorr),'residual_cross_correlations'),(pd.DataFrame(ranks),'control_rank_checks')]: save(frame,name)
 # Figures compare point responses only, avoiding false reassurance from inadequate residuals.
 for criterion in ['bic','aic']:
  fig,axes=plt.subplots(2,4,figsize=(15,7),sharex=True)
  for i,asset in enumerate(['btc','eth']):
   for j,shock in enumerate(SHOCKS):
    ax=axes[i,j]
    for spec,label in [('baseline','Baseline'),('weekday_gap','Weekday + elapsed days')]:
     q=irf[(irf.asset==asset)&(irf.regime=='full')&(irf.criterion==criterion)&(irf.shock==shock)&(irf.specification==spec)]
     ax.plot(q.horizon_sessions,q.response_pct,label=label,linewidth=1.5)
    ax.axhline(0,color='#888',linewidth=.7); ax.set_title(asset.upper()+' | '+shock); ax.set_xlabel('Eligible US sessions'); ax.set_ylabel('Log return (%)')
    if i==0 and j==0: ax.legend(fontsize=8)
  fig.suptitle(criterion.upper()+' | baseline vs calendar-controlled VAR | point IRFs, not causal effects',y=1.01)
  fig.tight_layout(); fig.savefig(OUT/('irf_comparison_'+criterion+'.png'),bbox_inches='tight'); plt.close(fig)
 summary=dict(scope='User-approved VAR calendar extension only; forecasting variance unchanged.',controls='Tuesday-Friday indicators, Monday reference; extra_calendar_days = elapsed calendar days - 1.',max_candidate_lag=10,minimum_fitted_lag=1,primary_whiteness_lags=20,secondary_whiteness_lags=30,n_models=len(diag),n_stable=int(diag.stable.sum()),combined_models_reject_5pct=int(compare.reject_whiteness_5pct.sum()),combined_models_total=len(compare),checks=checks,input_baseline_sha256=before)
 (OUT/'validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
 report(diag,compare,comp_irf)
 print(compare[['asset','regime','criterion','baseline_lag','lag','baseline_whiteness_p20','whiteness_p20','stable']].to_string(index=False),flush=True)
 return summary

def report(diag,comparison,irf):
 n=int(comparison.reject_whiteness_5pct.sum()); total=len(comparison)
 largest=irf.loc[irf.response_difference_pp.abs().nlargest(12).index][['asset','regime','criterion','shock','horizon_sessions','baseline_response_pct','response_pct','response_difference_pp']]
 summary=(f'Tất cả {len(diag)} hệ được ước lượng đều ổn định. Trong {total} hệ dùng đồng thời weekday và khoảng cách phiên, {n} hệ vẫn bác bỏ residual whiteness tại 5% (Portmanteau 20 lags). ' if diag.stable.all() else f'Có hệ VAR không ổn định; xem diagnostics. {n}/{total} hệ calendar bác bỏ whiteness. ')
 summary+=('Thêm calendar controls chưa giải quyết được hạn chế phần dư. Không thay baseline hoặc nâng kết quả này thành bằng chứng causal.' if n==total else 'Một số hệ không bác bỏ whiteness, nhưng đây không phải chứng minh phần dư độc lập hay mô hình đúng. Không chọn mô hình chỉ để vượt kiểm định.')
 def ht(f): return '<div class="table-wrap">'+f.to_html(index=False,border=0,float_format=lambda v:f'{v:.6g}')+'</div>'
 body='<h1>VAR bổ sung: lịch giao dịch và khoảng cách phiên</h1><p class="lead">'+summary+'</p>'
 body+='<h2>Phạm vi được đồng ý</h2><p>Chỉ bổ sung calendar controls cho VAR; không đổi snapshot, forecasting variance, LP hay event study. Báo cáo baseline được giữ riêng. Không mở rộng lag search để tìm p-value thuận lợi: cùng miền 0–10 như baseline, fitted lag tối thiểu 1, lựa chọn BIC và AIC riêng.</p>'
 body+='<h2>Đặc tả</h2><p>Hệ gồm ΔVIX, USD log return (%), Δ2Y (bps), Δ10Y (bps), crypto log return (%), thứ tự Cholesky giữ nguyên. So sánh baseline, weekday-only, gap-only và weekday+gap. Weekday là Tuesday–Friday dummy, Monday reference; gap = số ngày lịch giữa hai phiên đủ dữ liệu − 1. Hằng số giữ trong mọi phương trình. Kiểm tra đủ rank để tránh collinearity giữa Monday/weekend gap. Không có tương tác calendar × lag trong đặc tả này.</p><p>IRF giữ calendar path cố định, shock size +5 VIX points, +1% USD, +10 bps yield. Horizon là phiên đủ dữ liệu, không phải ngày UTC. Weekday/gap giải thích deterministic conditional mean; không tự điều chỉnh heteroskedasticity theo độ dài interval hoặc thay đổi dynamics theo từng loại phiên.</p>'
 body+='<h2>Kết quả so sánh trực tiếp</h2>'+ht(comparison[['asset','regime','criterion','baseline_lag','lag','baseline_nobs','nobs','baseline_whiteness_p20','whiteness_p20','whiteness_p30','stable','same_lag_as_baseline']])
 body+='<p>Primary whiteness: adjusted Portmanteau 20 lags; 30 lags là chẩn đoán bổ sung. Null là không có residual serial/cross correlation đến horizon kiểm định. P-value dùng phân phối tiệm cận của thư viện, không robust tuyệt đối với heavy tails/heteroskedasticity; không bác bỏ không xác nhận độc lập. Nếu selected lag đổi, chênh lệch IRF phản ánh cả controls và lag choice; cột same_lag_as_baseline cho biết trường hợp cùng lag và cùng effective sample.</p>'
 body+='<h2>IRF toàn mẫu</h2><img src="irf_comparison_bic.png" alt="BIC IRF comparison"><img src="irf_comparison_aic.png" alt="AIC IRF comparison"><p>Đồ thị chỉ trình bày point estimates, không dùng bands để che hạn chế phần dư. File impulse_responses.csv vẫn giữ pointwise asymptotic standard errors/95% intervals nhằm kiểm toán; chúng không được coi là inference đã được sửa sau khi thêm controls.</p>'
 body+='<h2>Những chênh lệch IRF lớn nhất</h2>'+ht(largest)+'<p>Chênh lệch tính theo điểm phần trăm log return. Đây là độ nhạy đặc tả, không phải kiểm định significance giữa hai ước lượng; không suy luận từ việc hai confidence intervals chồng nhau.</p>'
 body+='<h2>Toàn bộ đặc tả và chẩn đoán</h2>'+ht(diag[['asset','regime','specification','criterion','lag','nobs','n_parameters','stable','whiteness_p20']])
 body+='<p>Các bảng kèm theo: <a href="calendar_coefficients.csv">calendar coefficients</a>, <a href="residual_own_serial_tests.csv">residual own-serial diagnostics</a>, <a href="residual_cross_correlations.csv">residual cross-correlations</a>, <a href="lag_selection.csv">lag selection</a>, <a href="irf_comparison.csv">IRF comparison</a>. Univariate Ljung–Box được dùng để định vị phương trình còn own-autocorrelation, không thay cho kiểm định toàn hệ; coefficient p-values và IRF intervals vẫn là asymptotic exploratory.</p>'
 body+='<h2>Kết luận và bước dừng</h2><p>'+summary+'</p><p>Không tự thêm bootstrap, tăng lag tối đa, thêm biến vĩ mô hay thay mô hình variance. Những phương pháp bổ sung ngoài phạm vi vừa được đồng ý cần trao đổi trước. Phần này là phân tích mở rộng hồi cứu sau khi đã xem chẩn đoán baseline, không phải kiểm định confirmatory đăng ký trước.</p>'
 body+='<p><a href="../report.html">Báo cáo baseline</a> · <a href="../dashboard/index.html">Dashboard baseline</a> · Phương pháp: <a href="https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.var_model.VAR.html">statsmodels VAR with exog</a>, <a href="https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.var_model.VARResults.test_whiteness.html">Portmanteau whiteness</a>.</p>'
 css='body{font:15px/1.65 system-ui,sans-serif;color:#203247;background:#f1f5f8;margin:0}main{max-width:1200px;padding:40px;margin:auto;background:#fff}h1{font-size:32px;color:#095d82}h2{margin-top:32px;color:#095d82}.lead{padding:18px;border-left:4px solid #096b93;background:#edf5f9}.table-wrap{overflow:auto}table{border-collapse:collapse;font-size:12px;white-space:nowrap}th,td{padding:8px;border-bottom:1px solid #dde5ed;text-align:right}th{background:#eaf3f8}img{max-width:100%;height:auto}a{color:#096b93}@media(max-width:700px){main{padding:18px}h1{font-size:25px}}'
 (OUT/'report.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chủ đề 9: VAR calendar extension</title><style>'+css+'</style><main>'+body+'</main></html>',encoding='utf-8')
 txt='# VAR calendar extension\n\n'+summary+'\n\n## Bảng so sánh\n\n'+comparison[['asset','regime','criterion','baseline_lag','lag','baseline_whiteness_p20','whiteness_p20']].to_string(index=False)+'\n\nĐặc tả: Tuesday–Friday dummies (Monday reference) và elapsed_calendar_days−1; cùng lag search 0–10, fitted lag tối thiểu 1, BIC/AIC riêng. Baseline và forecasting không đổi. Báo cáo đầy đủ: [report.html](report.html).\n'
 (OUT/'report.md').write_text(txt,encoding='utf-8')

if __name__=='__main__': main()
