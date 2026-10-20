"""Fixed-split one-day forecasts; validation-only tuning; paired USD comparison."""
from research_common import *
import warnings,itertools
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import ElasticNet
from sklearn.ensemble import HistGradientBoostingRegressor
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from threadpoolctl import threadpool_limits

def estimator(kind,params):
 if kind=='elastic_net':
  return TransformedTargetRegressor(regressor=make_pipeline(StandardScaler(),ElasticNet(max_iter=20000,tol=1e-6,**params)),transformer=StandardScaler())
 return HistGradientBoostingRegressor(loss='squared_error',max_iter=200,learning_rate=.05,min_samples_leaf=30,early_stopping=False,random_state=9,**params)

def metrics(y,p,target):
 err=np.asarray(y)-np.asarray(p)
 result={'rmse':float(np.sqrt(np.mean(err**2))),'mae':float(np.mean(np.abs(err))),'mse':float(np.mean(err**2))}
 if target=='squared_return': result['qlike']=float(np.mean(np.log(p)+np.asarray(y)/p))
 else: result['direction_accuracy']=float(np.mean(np.sign(y)==np.sign(p)))
 return result

def main():
 cfg=json.loads((ROOT/'data/processed/research_design.json').read_text())
 scores=[]; tuning=[]; predictions=[]; selected=[]; timing=[]
 with threadpool_limits(limits=2):
  for asset,variant,target in itertools.product(['btc','eth'],['no_usd_long','common_no_usd','common_with_usd'],['return','squared_return']):
   f=pd.read_csv(ROOT/'data/processed'/f'forecast_{asset}_{variant}.csv',parse_dates=['date_utc','close_timestamp_utc','target_date_utc']).set_index('date_utc')
   features=cfg['assets'][asset]['with_usd_features' if variant=='common_with_usd' else 'base_features']
   col=f'{asset}_target_next_{target}'; tr=f[f.split=='train']; va=f[f.split=='validation']; te=f[f.split=='test']
   # At each boundary require that fitted labels have finished by the next forecast origin.
   assert ((tr.target_date_utc+pd.Timedelta(days=1))<=va.close_timestamp_utc.min()).all()
   dev=pd.concat([tr,va]); assert ((dev.target_date_utc+pd.Timedelta(days=1))<=te.close_timestamp_utc.min()).all()
   timing.append({'asset':asset,'variant':variant,'target':target,'validation_first_origin_utc':str(va.close_timestamp_utc.min()),'training_last_label_close_utc':str((tr.target_date_utc+pd.Timedelta(days=1)).max()),'test_first_origin_utc':str(te.close_timestamp_utc.min()),'development_last_label_close_utc':str((dev.target_date_utc+pd.Timedelta(days=1)).max())})
   def clamp(p): return np.maximum(p,1e-12) if target=='squared_return' else np.asarray(p)
   for kind in ['historical_mean','zero_return' if target=='return' else 'trailing30_variance','elastic_net','gradient_boosting']:
    if kind in ['elastic_net','gradient_boosting']:
     grid=([{'alpha':a,'l1_ratio':l} for a,l in itertools.product([.001,.01,.1],[.1,.9])] if kind=='elastic_net' else [{'max_leaf_nodes':leaf,'l2_regularization':reg} for leaf,reg in itertools.product([7,15],[1.,10.])])
     best=None
     for params in grid:
      model=estimator(kind,params)
      with warnings.catch_warnings(): warnings.simplefilter('ignore'); model.fit(tr[features],tr[col])
      vp=clamp(model.predict(va[features])); vm=metrics(va[col],vp,target)
      objective=vm['qlike' if target=='squared_return' else 'mse']
      tuning.append(dict(asset=asset,variant=variant,target=target,model=kind,params=json.dumps(params),validation_objective=objective))
      if best is None or objective<best[0]: best=(objective,params)
     model=estimator(kind,best[1]); model.fit(dev[features],dev[col]); pred=clamp(model.predict(te[features]))
     chosen=json.dumps(best[1]); valobj=best[0]
    elif kind=='historical_mean':
     pred=clamp(np.repeat(dev[col].mean(),len(te))); chosen='{}'; valobj=metrics(va[col],clamp(np.repeat(tr[col].mean(),len(va))),target)['qlike' if target=='squared_return' else 'mse']
    elif kind=='zero_return': pred=np.zeros(len(te)); chosen='{}'; valobj=float(np.mean(va[col]**2))
    else:
     pred=clamp(te[asset+'_vol30_annualized'].values**2/365); chosen='{}'; valobj=metrics(va[col],clamp(va[asset+'_vol30_annualized'].values**2/365),target)['qlike']
    out=metrics(te[col],pred,target)
    scores.append(dict(asset=asset,variant=variant,target=target,model=kind,n_test=len(te),validation_objective=valobj,**out))
    selected.append(dict(asset=asset,variant=variant,target=target,model=kind,selected_parameters=chosen,selection_data='validation only'))
    for date,actual,predicted in zip(te.index,te[col],pred): predictions.append(dict(date_utc=str(date.date()),asset=asset,variant=variant,target=target,model=kind,actual=float(actual),predicted=float(predicted)))
   print('Forecast completed:',asset,variant,target,flush=True)
 scores=pd.DataFrame(scores); pred=pd.DataFrame(predictions); tests=[]
 for asset,target,model in itertools.product(['btc','eth'],['return','squared_return'],['historical_mean','elastic_net','gradient_boosting']):
  q=pred[(pred.asset==asset)&(pred.target==target)&(pred.model==model)]
  no=q[q.variant=='common_no_usd'].set_index('date_utc'); yes=q[q.variant=='common_with_usd'].set_index('date_utc')
  assert no.index.equals(yes.index) and np.array_equal(no.actual,yes.actual)
  if target=='return': delta=(yes.actual-yes.predicted)**2-(no.actual-no.predicted)**2
  else: delta=np.log(yes.predicted/no.predicted)+yes.actual*(1/yes.predicted-1/no.predicted)
  # Paired loss difference, Newey-West lag 5. Irregular eligible origins, not all UTC days.
  fit=sm.OLS(delta.values,np.ones((len(delta),1))).fit(cov_type='HAC',cov_kwds={'maxlags':5,'use_correction':True})
  a=scores[(scores.asset==asset)&(scores.target==target)&(scores.model==model)&(scores.variant=='common_no_usd')].iloc[0]
  b=scores[(scores.asset==asset)&(scores.target==target)&(scores.model==model)&(scores.variant=='common_with_usd')].iloc[0]
  tests.append(dict(asset=asset,target=target,model=model,n_pairs=len(delta),mean_loss_with_minus_without=float(delta.mean()),hac_se=float(fit.bse[0]),pvalue=float(fit.pvalues[0]) if fit.bse[0]>0 else 1.,rmse_without=a.rmse,rmse_with=b.rmse,rmse_improvement_pct=100*(a.rmse-b.rmse)/a.rmse))
 tests=pd.DataFrame(tests); tests['qvalue_bh']=multipletests(tests.pvalue,method='fdr_bh')[1]
 table(scores,'forecast_test_metrics'); table(pd.DataFrame(tuning),'forecast_validation_search'); table(pd.DataFrame(selected),'forecast_selected_parameters'); table(pred,'forecast_test_predictions'); table(tests,'forecast_usd_paired_tests'); table(pd.DataFrame(timing),'forecast_label_availability_checks')
 variance=pred[pred.target=='squared_return']
 floors=variance.groupby(['asset','variant','model']).agg(n_test=('predicted','size'),floor_hits=('predicted',lambda x:int((x<=1.00001e-12).sum()))).reset_index()
 floors['floor_fraction']=floors.floor_hits/floors.n_test
 table(floors,'forecast_variance_floor_diagnostics')
 fig,axes=plt.subplots(1,2,figsize=(12,4.5))
 for ax,target in zip(axes,['return','squared_return']):
  q=tests[(tests.target==target)&(tests.model!='historical_mean')]
  labels=q.asset.str.upper()+' / '+q.model.str.replace('_',' ')
  ax.barh(labels,q.rmse_improvement_pct,color=['#096b93' if x>=0 else '#b45c77' for x in q.rmse_improvement_pct]); ax.axvline(0,color='#555',linewidth=.8); ax.set_xlabel('RMSE improvement from adding USD (%)'); ax.set_title('Next-day '+target.replace('_',' '))
 fig.suptitle('Matched 2019+ samples | untouched test 2025 onward'); fig.tight_layout(); figure(fig,'forecast_usd_comparison')
 js({'protocol':'Hyperparameters selected on fixed 2023-24 validation; refit once on train+validation; fixed parameters during 2025+ test. One-step features update each origin. No test tuning.','models':'Historical mean; zero return or trailing30 variance; scaled Elastic Net; histogram gradient boosting.','variance_floor':1e-12,'variance_metric':'QLIKE = mean(log(predicted_variance)+observed_squared_return/predicted_variance), lower is better; constants omitted.','variance_target':'Squared daily return is a noisy variance proxy, not intraday realized volatility.','paired_test':'Two-sided HAC lag5 intercept test of with-USD minus without-USD loss; BH adjustment across reported comparisons. Forecasts are nested and origin dates irregular, so test is an approximate robustness diagnostic.','limitations':'Market feed lag1 proxies and retrospective crypto prices remain; snapshot-based macro PIT does not certify whole feed as fully real time. Common pre2020 segment has only 229 observations.'},'forecast_method')
 print(tests.to_string(index=False),flush=True)
if __name__=='__main__': main()
