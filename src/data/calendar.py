"""Calendar panel of last-admitted levels; retain raw and historical panels untouched."""
from src.utils.project import *

def prepare():
    init();d=pd.read_csv(ROOT/'data/processed/daily_research_latest.csv',parse_dates=['date_utc']).set_index('date_utc')
    f=pd.read_csv(ROOT/'data/processed/forecast_origins_vintage_macro.csv',parse_dates=['date_utc']).set_index('date_utc')
    assert d.index.equals(pd.date_range(d.index.min(),d.index.max(),name='date_utc'))
    p=pd.DataFrame(index=d.index);p['information_row_date']=p.index-pd.Timedelta(days=2)
    # f row D-2 reference close = D-1 midnight, a full day before origin D.
    for source,name,kind in [('broad_usd','usd_return_pct','log'),('us2y','us2y_change_bps','bps'),('us10y','us10y_change_bps','bps'),('fed_funds','fed_funds_change_bps','bps'),('nfci','nfci_change','diff')]:
        level=f[source+'_pit'].shift(2).ffill();p[source+'_available']=level
        p[name]=100*np.log(level).diff() if kind=='log' else level.diff()*(100 if kind=='bps' else 1)
        for suffix in ['_pit_obs_date','_pit_vintage_date']:p[source+suffix]=f[source+suffix].shift(2).ffill()
    p['vix_available_proxy']=d.vix.shift(3).ffill();p['vix_observation_date_proxy']=pd.Series(d.index.where(d.vix.notna()),index=d.index).shift(3).ffill()
    p['vix_change']=p.vix_available_proxy.diff();p['stress']=(p.vix_available_proxy>30).astype(int);p['post2020']=(p.index>='2020-01-01').astype(int)
    for a in ['btc','eth']:
        p[a+'_return_pct']=d[a+'_usd_log_return']*100
        p[a+'_prior_return_pct']=p[a+'_return_pct'].shift(2)
        p[a+'_prior_vol30']=d[a+'_vol30_annualized'].shift(2)
    p.to_csv(PANELS/'calendar_information.csv',encoding='utf-8-sig',float_format='%.17g')
    # Purely historical observation-date carry for visual comparison, NEVER used as PIT features.
    levels=d[['vix','broad_usd','us2y','us10y','fed_funds']].ffill()
    levels.to_csv(PANELS/'historical_levels_carried_EXPOST.csv',encoding='utf-8-sig',float_format='%.17g')
    dictionary=[dict(variable=c,role=('target/history only' if c.endswith('_return_pct') and 'prior' not in c else 'information/metadata'),timing='origin D midnight; f information D-2 / VIX observation <=D-3; crypto targets not filled',interpretation='available-information update includes revisions; not identified surprise') for c in p]
    csv(pd.DataFrame(dictionary),'calendar_dictionary.csv')
    print('Prepared calendar levels/changes:',len(p),'rows; USD PIT remains unavailable before 2019.',flush=True)
