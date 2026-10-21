"""Read-only replay of frozen historical outer folds; never fits or logs live forecasts."""
from pathlib import Path
import json

import joblib
from threadpoolctl import threadpool_limits
from research_common import ROOT, pd, np
from src.utils.project import sha
from research_completion import features, model_predict

VERSION = 'pit_nested_20261020'
OUT = ROOT/'outputs/research'/VERSION
PANELS = ROOT/'data/processed'/VERSION
MODELS = ROOT/'models'/VERSION
CONFIG = ROOT/'config'/f'{VERSION}.json'
DATA = ROOT/'dashboard/historical_oos_data.json'
AUDIT = ROOT/'dashboard/historical_oos_audit.json'
KINDS = ['elastic_net', 'gradient_boosting', 'historical_mean', 'natural_benchmark']
KEYS = ['asset', 'scenario', 'variant', 'target']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def key(parts):
    return '|'.join(map(str, parts))


def inputs():
    paths = [CONFIG, MODELS/'freeze.json']
    paths += [OUT/n for n in ['model_inventory.csv', 'outer_predictions.csv', 'fold_timing.csv',
                              'selected_parameters.csv', 'prepared_input_lock.json', 'fit_code_lock.json']]
    paths += sorted(PANELS.glob('*.csv'))
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def verify_frozen():
    frozen = read(MODELS/'freeze.json')
    assert frozen['config_sha256'] == sha(CONFIG)
    assert frozen['inventory_sha256'] == sha(OUT/'model_inventory.csv')
    assert frozen['predictions_sha256'] == sha(OUT/'outer_predictions.csv')
    for name in ['prepared_input_lock.json', 'fit_code_lock.json']:
        for path, digest in read(OUT/name)['files'].items():
            assert sha(ROOT/path) == digest, f'Frozen historical input changed: {path}'


def assemble():
    """Compact exact predictions; each date keeps all four model/benchmark values."""
    f = pd.read_csv(OUT/'outer_predictions.csv', float_precision='round_trip')
    assert not f.duplicated(KEYS+['outer_year', 'origin_utc', 'model']).any()
    series = {}
    for group, g in f.groupby(KEYS, sort=True):
        assert set(g.model) == set(KINDS)
        actual = g.groupby('origin_utc').actual.agg(['first', 'nunique'])
        assert actual['nunique'].eq(1).all()
        pivot = g.pivot(index='origin_utc', columns='model', values='predicted').sort_index()
        assert pivot[KINDS].notna().all().all()
        series[key(group)] = [[date, float(actual.loc[date, 'first']),
                              *[float(row[kind]) for kind in KINDS], int(date[:4])]
                             for date, row in pivot.iterrows()]
    timing = pd.read_csv(OUT/'fold_timing.csv')
    inventory = pd.read_csv(OUT/'model_inventory.csv')
    selected = pd.read_csv(OUT/'selected_parameters.csv')
    folds = {}
    for group, g in timing.groupby(KEYS+['outer_year'], sort=True):
        outer = g[g.stage.eq('outer')]
        assert len(outer) == 1 and len(g[g.stage.eq('inner')]) == 2
        row = outer.iloc[0]
        fit = pd.Timestamp(row.fold_start)-pd.Timedelta(days=1)
        assert pd.Timestamp(row.fit_cutoff) == fit
        assert pd.Timestamp(row.last_fit_label_available) <= fit
        assert pd.Timestamp(row.last_tuning_label_available) <= fit
        for r in g.to_dict('records'):
            assert pd.Timestamp(r['last_fit_label_available']) <= pd.Timestamp(r['fit_cutoff'])
            assert pd.Timestamp(r['first_evaluate_origin']) >= pd.Timestamp(r['fold_start'])
        match = np.logical_and.reduce([inventory[c].eq(v) for c, v in zip(KEYS+['outer_year'], group)])
        models = inventory[match]
        assert set(models.model) == set(KINDS[:2]) and len(models) == 2
        settings = selected[np.logical_and.reduce([selected[c].eq(v) for c, v in zip(KEYS+['outer_year'], group)])]
        folds[key(group)] = dict(fit_start=str(pd.Timestamp(row.fold_start).date()),
            fit_cutoff=str(fit.date()), last_fit_label_available=str(pd.Timestamp(row.last_fit_label_available).date()),
            last_tuning_label_available=str(pd.Timestamp(row.last_tuning_label_available).date()), n_fit=int(row.n_fit),
            model_sha256={r.model: r.sha256 for r in models.itertuples()},
            parameters={r.model: json.loads(r.parameters) for r in settings.itertuples()},
            inner=[{c: str(r[c]) for c in ['fold_start', 'fit_cutoff', 'last_fit_label_available',
                                          'first_evaluate_origin', 'last_tuning_label_available']}
                   for r in g[g.stage.eq('inner')].to_dict('records')])
    dates = [r[0] for rows in series.values() for r in rows]
    return dict(version='historical_oos_replay_20261021', mode='historical_pseudo_oos',
        date_min=min(dates), date_max=max(dates),
        columns=['origin_utc', 'actual', *KINDS, 'outer_year'], series=series, folds=folds,
        interpretation='Historical chronological outer-fold replay; final project design used previously viewed outcomes.',
        receipt_basis='Historical availability assumed from dates and ALFRED vintages; not actual archived live receipts.',
        models_refit=0, live_forecasts_created=0)


def replay():
    """Independently reconstruct fold timing and replay every artifact and benchmark."""
    verify_frozen()
    saved = pd.read_csv(OUT/'outer_predictions.csv', float_precision='round_trip')
    groups = {k: g.sort_values('origin_utc') for k, g in saved.groupby(KEYS+['outer_year', 'model'])}
    inventory = pd.read_csv(OUT/'model_inventory.csv')
    selected = pd.read_csv(OUT/'selected_parameters.csv').set_index(KEYS+['outer_year', 'model'])
    assert len(inventory) == 640
    panels = {}
    learned_rows = benchmark_rows = 0
    max_error = 0.
    with threadpool_limits(limits=2):
        for i, r in enumerate(inventory.to_dict('records')):
            panel_key = (r['asset'], r['scenario'], r['variant'], r['target'])
            if panel_key[:3] not in panels:
                asset, scenario, variant = panel_key[:3]
                g = pd.read_csv(PANELS/f'{asset}_{variant}_{scenario}.csv', float_precision='round_trip',
                    parse_dates=['origin_utc', 'information_date', 'assumed_available_utc',
                                 'label_close_utc', 'label_assumed_available_utc']).set_index('origin_utc')
                lag = 4 if scenario == 'matched_asof_d4' else 3
                assert g.index.is_unique and g.index.is_monotonic_increasing
                assert (g.information_date == g.index-pd.Timedelta(days=lag)).all()
                assert (g.assumed_available_utc == g.information_date+pd.Timedelta(days=2)).all()
                assert (g.assumed_available_utc <= g.index-pd.Timedelta(days=1)).all()
                assert (g.label_close_utc == g.index+pd.Timedelta(days=1)).all()
                assert (g.label_assumed_available_utc == g.index+pd.Timedelta(days=2)).all()
                panels[panel_key[:3]] = g
            g = panels[panel_key[:3]]
            start = pd.Timestamp(int(r['outer_year']), 1, 1)
            cutoff = start-pd.Timedelta(days=1)
            tr = g[(g.index < start) & (g.label_assumed_available_utc <= cutoff)]
            te = g[(g.index >= start) & (g.index < pd.Timestamp(int(r['outer_year'])+1, 1, 1))]
            path = ROOT/r['file']
            assert sha(path) == r['sha256']
            artifact = joblib.load(path)
            cols = features(r['asset'], r['variant'])
            assert artifact['features'] == cols and artifact['config_sha256'] == sha(CONFIG)
            assert pd.Timestamp(artifact['simulated_fit_cutoff_utc']) == cutoff
            assert artifact['last_fit_label_available'] == str(tr.label_assumed_available_utc.max())
            assert len(tr) == int(r['n_fit']) and tr.index.max() < te.index.min()
            group = (*panel_key, int(r['outer_year']), r['model'])
            assert artifact['parameters'] == json.loads(selected.loc[group, 'parameters'])
            y = tr['actual_'+r['target']]
            fitted = artifact['fitted']
            assert np.isclose(fitted[1], y.mean() if r['target'] == 'squared_return' else 1., rtol=1e-14, atol=0)
            if r['model'] == 'elastic_net':
                scaler = fitted[0].regressor_.named_steps['standardscaler']
                np.testing.assert_allclose(scaler.mean_, tr[cols].mean().to_numpy(), rtol=1e-12, atol=1e-12)
                transformed = np.log(y.to_numpy()/fitted[1]+1e-12) if r['target'] == 'squared_return' else y.to_numpy()
                assert np.isclose(fitted[0].transformer_.mean_[0], transformed.mean(), rtol=1e-12, atol=1e-12)
            q = groups[group]
            expected = model_predict(fitted, te[cols], r['model'], r['target'])
            assert np.array_equal(pd.to_datetime(q.origin_utc).to_numpy(), te.index.to_numpy())
            assert np.array_equal(q.actual.to_numpy(), te['actual_'+r['target']].to_numpy())
            np.testing.assert_allclose(q.predicted.to_numpy(), expected, rtol=1e-13, atol=1e-15)
            max_error = max(max_error, float(np.max(np.abs(q.predicted.to_numpy()-expected))))
            learned_rows += len(q)
            if (i+1) % 160 == 0:
                print(f'Historical replay: {i+1}/640 artifacts verified; no fit', flush=True)
        for group, q in groups.items():
            asset, scenario, variant, target, year, kind = group
            if kind not in KINDS[2:]:
                continue
            g = panels[(asset, scenario, variant)]
            start = pd.Timestamp(int(year), 1, 1)
            tr = g[(g.index < start) & (g.label_assumed_available_utc <= start-pd.Timedelta(days=1))]
            te = g.loc[pd.to_datetime(q.origin_utc)]
            expected = np.repeat(tr['actual_'+target].mean(), len(q)) if kind == 'historical_mean' else (
                np.zeros(len(q)) if target == 'return' else te[asset+'_vol30_annualized'].to_numpy()**2/365)
            np.testing.assert_allclose(q.predicted.to_numpy(), expected, rtol=1e-13, atol=1e-15)
            assert np.array_equal(q.actual.to_numpy(), te['actual_'+target].to_numpy())
            benchmark_rows += len(q)
    assert learned_rows+benchmark_rows == len(saved)
    return dict(passed=True, artifacts_replayed=len(inventory), panel_count=len(panels),
        learned_predictions_checked=learned_rows, benchmark_predictions_checked=benchmark_rows,
        total_prediction_rows=len(saved), max_absolute_replay_error=max_error,
        fold_chronology_checked=True, train_only_scaling_checked=True,
        models_refit=0, live_forecasts_created=0, future_performance_scored=False)


def prepare():
    """Explicitly regenerate source-controlled, public derived display data only."""
    validation = replay()
    payload = assemble()
    DATA.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n', encoding='utf-8')
    audit = dict(version=payload['version'], audited_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),
        data_sha256=sha(DATA), input_hashes=inputs(), validation=validation)
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(validation), flush=True)


def load():
    audit = read(AUDIT)
    assert audit['data_sha256'] == sha(DATA), 'Historical dashboard payload changed'
    assert all(sha(ROOT/n) == digest for n, digest in audit['input_hashes'].items()), 'Historical source changed'
    payload = read(DATA)
    payload['audit'] = dict(audit['validation'], audited_at_utc=audit['audited_at_utc'],
                           data_sha256=audit['data_sha256'])
    return payload


def validate():
    payload = load()
    displayed = dict(payload)
    displayed.pop('audit')
    assert displayed == assemble(), 'Historical dates/predictions/fold metadata differ from sources'
    result = replay()
    expected = read(AUDIT)['validation']
    assert all(result[k] == v for k, v in expected.items() if k != 'max_absolute_replay_error'), 'Frozen replay changed'
    folder = ROOT/'.verification/historical_oos_20261021'
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
    return result
