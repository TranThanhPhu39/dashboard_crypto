"""Persist approved models and compute validation-only grouped feature importance."""
from src.utils.project import *
from research_completion import VARIANTS,features,read_panel,split_panel,model_fit,model_predict,losses
from threadpoolctl import threadpool_limits
import joblib

def run():
    init()
    log=OUT/'prospective_predictions.jsonl'
    assert not log.exists() or not log.read_text(encoding='utf-8').strip(), 'Artifacts frozen after prospective logging starts; use a new version.'
    params=pd.read_csv(RESULTS/'completion/selected_parameters.csv');prior=pd.read_csv(RESULTS/'completion/test_predictions.csv',float_precision='round_trip');artifacts=[];importance=[];rng=np.random.default_rng(9)
    with threadpool_limits(limits=2):
        for row in params.itertuples():
            if row.model not in ['elastic_net','gradient_boosting']:continue
            f=read_panel(row.asset,row.variant);tr,va,dev,te=split_panel(f);cols=features(row.asset,row.variant);target='actual_'+row.target;settings=json.loads(row.parameters)
            fit=model_fit(row.model,settings,dev[cols],dev[target],row.target)
            pred=model_predict(fit,te[cols],row.model,row.target);q=prior[(prior.asset==row.asset)&(prior.variant==row.variant)&(prior.target==row.target)&(prior.model==row.model)]
            assert np.allclose(pred,q.predicted,rtol=1e-9,atol=1e-12)
            name=f'{row.asset}_{row.variant}_{row.target}_{row.model}.joblib';file=MODELS/name
            payload=dict(fitted=fit,features=cols,asset=row.asset,variant=row.variant,target=row.target,kind=row.model,parameters=settings,last_fit_label_available=str(dev.label_assumed_available_utc.max()),forecast_origin_rule='24h buffered completion design; row t predicts UTC day t+1',sklearn_version=__import__('sklearn').__version__)
            joblib.dump(payload,file)
            artifacts.append(dict(file=file.relative_to(ROOT).as_posix(),sha256=sha(file),asset=row.asset,variant=row.variant,target=row.target,model=row.model,last_fit_label_available=payload['last_fit_label_available'],n_fit=len(dev)))
            # Importance is computed on validation using a model fitted on training only.
            vfit=model_fit(row.model,settings,tr[cols],tr[target],row.target);vp=model_predict(vfit,va[cols],row.model,row.target);base=float(losses(va[target],vp,row.target).mean())
            groups={'own_crypto':[c for c in cols if c.startswith(row.asset+'_')],'macro_without_USD':[c for c in cols if not c.startswith(row.asset+'_') and c!='broad_usd_pit_change'],'USD':[c for c in cols if c=='broad_usd_pit_change']}
            for group,groupcols in groups.items():
                if not groupcols:continue
                for rep in range(10):
                    offset=int(rng.integers(30,len(va)-30));xx=va[cols].copy();xx[groupcols]=np.roll(xx[groupcols].to_numpy(),offset,axis=0)
                    pp=model_predict(vfit,xx,row.model,row.target);importance.append(dict(asset=row.asset,variant=row.variant,target=row.target,model=row.model,feature_group=group,repeat=rep,circular_shift=offset,validation_baseline_loss=base,loss_increase=float(losses(va[target],pp,row.target).mean()-base)))
            print('Saved artifact / validation importance:',name,flush=True)
    csv(pd.DataFrame(artifacts),'model_inventory.csv');csv(pd.DataFrame(importance),'validation_group_importance.csv')
    save_json(MODELS/'model_card.json',dict(training='unchanged approved completion fits; test previously inspected',security='load only these locally generated joblib artifacts, verified by SHA256',importance='validation-only circular permutation groups, descriptive; correlated features and selection on same validation limit inference',next_test='future prediction log starting 2026-10-20, not evaluated here'))
