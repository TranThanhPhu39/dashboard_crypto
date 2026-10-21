"""Operational scheduling/health only. No model fitting or loss evaluation."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv
import hashlib
import html
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/automation_20261020'
CONFIG = ROOT/'config/automation_20261020.json'
UTC = timezone.utc
POWERSHELL = Path(os.environ.get('SystemRoot', r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'


def now_utc():
    return datetime.now(UTC)


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Operational timestamps require an explicit timezone')
    return result.astimezone(UTC)


def read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, prefix=path.name+'.', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.flush(); os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class AlreadyRunningError(RuntimeError):
    pass


class HostedAuthorityError(RuntimeError):
    pass


def assert_writer_allowed(folder=None):
    installation=read_json(Path(folder or OUT)/'installation.json', {})
    if installation.get('provider')=='github-actions' and os.environ.get('GITHUB_ACTIONS')!='true':
        raise HostedAuthorityError('GitHub owns the live ledger. This local copy is read-only; pause and transfer ownership before running a local worker.')


@contextmanager
def process_lock(path):
    """OS lock is released automatically on exit/crash; never delete live locks."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open('a+b')
    if path.stat().st_size == 0:
        stream.write(b'0'); stream.flush()
    stream.seek(0)
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        stream.close()
        raise AlreadyRunningError(str(path)) from exc
    try:
        yield
    finally:
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def automation_summary(folder=OUT):
    """Return persisted facts, so build/validation see the same snapshot."""
    folder = Path(folder)
    scheduler = read_json(folder/'scheduler_status.json', {})
    state = read_json(folder/'state.json', {})
    health = read_json(folder/'health.json', {})
    installation = read_json(folder/'installation.json', {})
    tasks = scheduler.get('tasks', [])
    installed = bool(state.get('status')!='finished_schedule' and installation.get('registered') and scheduler.get('verified') and len(tasks)==2
                     and all(task.get('enabled') and task.get('action_matches') for task in tasks))
    if scheduler.get('provider') == 'github-actions':
        return dict(installed=installed, provider='github-actions', schedule='GitHub Actions: mỗi giờ phút 15 (UTC; có thể trễ)',
                monitor_schedule='GitHub Actions: mỗi giờ phút 45 (UTC; có thể trễ)',
                scheduler_checked_at_utc=scheduler.get('checked_at_utc'),
                next_run_local=next((row.get('next_run_local') for row in tasks if row.get('role')=='pipeline'), None),
                latest_status=state.get('status', 'not_run'), last_success_utc=state.get('last_success_utc'),
                health_status=health.get('status', 'not_checked'), active_alerts=len(health.get('issues', [])),
                health_checked_at_utc=health.get('checked_at_utc'), desktop_notifications=False,
                requirements='Chạy trên GitHub, không cần bật máy cá nhân. Lịch có thể trễ; receipt và cutoff dùng thời điểm thực, không bù dự báo quá hạn.')
    return dict(installed=installed, provider='windows', schedule='Mỗi giờ phút 15; thêm khi đăng nhập',
                monitor_schedule='Mỗi giờ phút 45; thêm khi đăng nhập',
                scheduler_checked_at_utc=scheduler.get('checked_at_utc'),
                next_run_local=next((row.get('next_run_local') for row in tasks if row.get('role')=='pipeline'), None),
                latest_status=state.get('status', 'not_run'), last_success_utc=state.get('last_success_utc'),
                health_status=health.get('status', 'not_checked'), active_alerts=len(health.get('issues', [])),
                health_checked_at_utc=health.get('checked_at_utc'),
                desktop_notifications=installation.get('desktop_notifications', False),
                requirements='Máy bật, tài khoản Admin đăng nhập và có Internet; chạy bù không tạo lại forecasts quá hạn.')


def automation_description(summary):
    if summary.get('latest_status')=='finished_schedule':
        return 'Lịch vận hành đã kết thúc theo stop_after_utc của thiết kế đã khóa.'
    if summary.get('provider') == 'github-actions':
        return ('Tự động trên GitHub Actions: pipeline mỗi giờ phút 15, giám sát phút 45; không cần bật máy cá nhân. '
                'Lịch có thể trễ; cutoff và thời điểm nhận dữ liệu giữ nguyên.' if summary['installed'] else
                'Chưa xác minh được lịch GitHub Actions đang bật; kiểm tra workflow và trạng thái vận hành.')
    return ('Đã cài lịch pipeline mỗi giờ phút 15 và giám sát phút 45; chạy thêm khi đăng nhập. '
            'Máy cần bật, tài khoản Admin đăng nhập và có Internet.' if summary['installed'] else
            'Chưa xác minh được hai tác vụ Windows đang bật; xem trạng thái giám sát.')


def check_immutable(cfg, root=ROOT):
    for name, expected in cfg['immutable_inputs'].items():
        path = (Path(root)/name).resolve()
        if not path.is_relative_to(Path(root).resolve()) or digest(path) != expected:
            raise AssertionError('Protected research input changed: '+name)


def needs_refresh(now, cfg, root=ROOT):
    pointer = read_json(Path(root)/'outputs/research/evidence_20261019/prospective/latest_capture.json', {})
    if not pointer.get('manifest'):
        return True
    manifest_path = Path(root)/pointer['manifest']
    if digest(manifest_path) != pointer['sha256']:
        raise AssertionError('Capture manifest integrity failure')
    capture = read_json(manifest_path)
    if os.environ.get('TOPIC09_FRED_TRANSPORT')=='official-api':
        from src.data.github_fred_api import VERSION
        if capture.get('transport_version')!=VERSION:
            # One immutable capture proves the new transport at handoff. Old
            # receipts remain eligible under the original earliest-input rule.
            return True
    return (now-timestamp(capture['capture_started_utc']) >= timedelta(hours=cfg['refresh_capture_hours'])
            or len(capture['sources']) != 17 or any(row['status']!='ok' for row in capture['sources']))


def capture_complete(root=ROOT):
    pointer = read_json(Path(root)/'outputs/research/evidence_20261019/prospective/latest_capture.json', {})
    return pointer.get('sources_ok') == pointer.get('sources_total') == 17


def health_issues(now, cfg, installation, scheduler, state, readiness=()):
    """Execution/availability checks only; no outcomes or forecast errors read."""
    issues = []
    def add(key, message):
        issues.append(dict(key=key, message=message))
    if not scheduler.get('verified') or not all(task.get('enabled') and task.get('action_matches') for task in scheduler.get('tasks', [])) or len(scheduler.get('tasks', []))!=2:
        add('scheduler_unavailable', 'Không xác minh được hai lịch chạy hoặc một lịch đang tắt/sai action.')
    for task in scheduler.get('tasks', []):
        if task.get('role')=='monitor' and task.get('last_task_result',0) not in (0,267009,267011,267033):
            add('monitor_task_failed', 'Tác vụ giám sát có mã lỗi Windows; kiểm tra log monitor và Task Scheduler.')
    if state.get('status')=='failed':
        add('pipeline_failed', 'Pipeline lỗi sau các lần thử; xem log: '+str(state.get('log', '')))
    last = state.get('last_success_utc') or installation.get('installed_at_utc')
    if state.get('status')!='finished_schedule' and last and now-timestamp(last)>timedelta(minutes=cfg['stale_after_minutes']):
        add('missed_runs', 'Quá thời gian dự kiến chưa có lần pipeline thành công; kiểm tra máy, tài khoản, mạng và Task Scheduler.')
    if state.get('status')=='running' and now-timestamp(state['started_at_utc'])>timedelta(minutes=cfg['task_execution_limit_minutes']):
        add('pipeline_hung', 'Lần chạy đang vượt giới hạn thời gian; watchdog sẽ giữ cảnh báo cho tới khi phục hồi.')
    installed = timestamp(installation['installed_at_utc']) if installation.get('installed_at_utc') else now
    for row in readiness:
        if str(row['market_day_is_weekend']).lower()=='true':
            continue
        deadline = timestamp(row['receipt_cutoff_utc'])
        origin = timestamp(row['origin_utc'])
        ready = str(row['long_features_ready_from_archived_receipts']).lower()=='true' and str(row['common_features_ready_from_archived_receipts']).lower()=='true'
        if installed>deadline or ready or now>=origin:
            continue
        if deadline<now:
            add('receipt_missed_'+origin.date().isoformat(), 'Origin '+origin.date().isoformat()+': đã qua receipt cutoff nhưng inputs chưa đủ. Không bù forecast hồi tố.')
        elif deadline-now<=timedelta(minutes=cfg['cutoff_warning_minutes']):
            add('receipt_risk_'+origin.date().isoformat(), 'Origin '+origin.date().isoformat()+': gần receipt cutoff nhưng inputs chưa đủ; kiểm tra nguồn hoặc holiday.')
    return issues


def notify(title, message, installation, root=ROOT):
    app_id = installation.get('toast_app_id')
    if not app_id:
        return dict(submitted=False, reason='No desktop notification AppUserModelID')
    try:
        result = subprocess.run([str(POWERSHELL), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden',
            '-File', str(Path(root)/'tools/notify_topic09.ps1'), '-Title', title, '-Message', message, '-AppId', app_id],
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=25,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        return dict(submitted=result.returncode==0, returncode=result.returncode,
                    detail=(result.stdout+result.stderr)[-1200:])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return dict(submitted=False, reason=str(exc))


def send_health_notifications(issues, cfg, installation, folder=OUT, sender=notify, now=None):
    folder=Path(folder); now=now or now_utc()
    previous=read_json(folder/'notification_state.json', {})
    sent=previous.get('sent', {}); deliveries=[]
    for issue in issues:
        last=sent.get(issue['key'])
        if last and now-timestamp(last)<timedelta(minutes=cfg['notification_cooldown_minutes']):
            continue
        delivery=sender('Topic09 - Can kiem tra pipeline', issue['message'], installation)
        deliveries.append(dict(key=issue['key'], **delivery))
        if delivery.get('submitted'):
            sent[issue['key']]=now.isoformat()
    if previous.get('active') and not issues and any(key in sent for key in previous['active']):
        deliveries.append(dict(key='recovered', **sender('Topic09 - Pipeline da phuc hoi', 'Các cảnh báo vận hành trước đó đã được giải quyết.', installation)))
    atomic_json(folder/'notification_state.json', dict(sent=sent, active=[row['key'] for row in issues],
                checked_at_utc=now.isoformat(), deliveries=deliveries))
    return deliveries


def refresh_scheduler_status(root=ROOT):
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        from src.github_scheduler import refresh
        refresh(Path(root))
        return
    result=subprocess.run([str(POWERSHELL), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden',
        '-File', str(Path(root)/'tools/manage_topic09_automation.ps1'), '-Action', 'Status'],
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=40,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if result.returncode:
        atomic_json(Path(root)/'outputs/automation_20261020/scheduler_status.json',
                    dict(verified=False, checked_at_utc=now_utc().isoformat(), tasks=[], error=(result.stdout+result.stderr)[-1200:]))


def write_health_page(health, state, folder=OUT):
    folder=Path(folder)
    items=''.join('<li>'+html.escape(issue['message'])+'</li>' for issue in health['issues']) or '<li>Không có cảnh báo vận hành đang mở.</li>'
    local_clock=lambda value: timestamp(value).astimezone(timezone(timedelta(hours=7))).strftime('%H:%M:%S ngày %d/%m/%Y') if value else 'chưa có'
    checked_local=local_clock(health['checked_at_utc'])
    success_local=local_clock(state.get('last_success_utc'))
    status_label='Hoạt động bình thường' if health['status']=='healthy' else 'Cần kiểm tra'
    body=f'''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Topic09 — Vận hành tự động</title><style>body{{font:16px/1.65 system-ui;background:#edf3f6;color:#193849;margin:0}}main{{max-width:1050px;margin:24px auto;background:white;padding:28px;border-radius:12px}}a{{color:#08678a}}p,li{{overflow-wrap:anywhere}}@media(max-width:700px){{main{{margin:0;padding:18px}}}}</style><main><h1>Vận hành tự động Topic09</h1><p><a href="../research/release_20261025/report.html">Báo cáo</a> · <a href="../research/release_20261025/oos_followup.html">Lịch OOS</a> · <a href="health.json">Chi tiết health</a> · <a href="scheduler_status.json">Windows Task Scheduler</a></p><p>Kiểm tra UTC: {html.escape(health['checked_at_utc'])}. Trạng thái: <strong>{html.escape(health['status'])}</strong>.</p><p>Lịch pipeline mỗi giờ phút 15; giám sát mỗi giờ phút 45; chạy thêm khi đăng nhập. Máy cần bật, tài khoản Admin đăng nhập và có Internet. Task yêu cầu wake khi Windows hỗ trợ; không thay power policy.</p><p>Lần thành công UTC: {html.escape(str(state.get('last_success_utc','chưa có')))}. Trạng thái lần chạy: {html.escape(state.get('status','not_run'))}.</p><ul>{items}</ul><p><a href="state.json">Trạng thái lần chạy và đường dẫn log</a>. Cảnh báo chỉ nói về vận hành và inputs; không đánh giá predictive skill. Ngày không đủ inputs vẫn được ghi rõ, không thay cutoff hoặc bù forecasts quá hạn.</p></main></html>'''
    body=body.replace('Kiểm tra UTC: '+html.escape(health['checked_at_utc']), 'Kiểm tra giờ Việt Nam: '+checked_local)
    body=body.replace('<strong>'+health['status']+'</strong>', '<strong>'+status_label+'</strong>')
    body=body.replace('Lần thành công UTC: '+html.escape(str(state.get('last_success_utc','chưa có'))), 'Lần thành công giờ Việt Nam: '+success_local)
    summary=automation_summary(folder)
    if summary.get('provider')=='github-actions':
        body=body.replace('Windows Task Scheduler', 'GitHub Actions scheduler')
        body=body.replace('Lịch pipeline mỗi giờ phút 15; giám sát mỗi giờ phút 45; chạy thêm khi đăng nhập. Máy cần bật, tài khoản Admin đăng nhập và có Internet. Task yêu cầu wake khi Windows hỗ trợ; không thay power policy.', automation_description(summary))
    (folder/'health.html').write_text(body, encoding='utf-8')


def monitor(refresh=True, root=ROOT, folder=OUT):
    root=Path(root); folder=Path(folder); cfg=read_json(root/'config/automation_20261020.json')
    if refresh:
        refresh_scheduler_status(root)
    installation=read_json(folder/'installation.json', {})
    scheduler=read_json(folder/'scheduler_status.json', {})
    state=read_json(folder/'state.json', {})
    source=root/'outputs/research/evidence_20261019/prospective_operations/readiness_calendar.csv'
    with source.open(encoding='utf-8-sig', newline='') as stream:
        readiness=list(csv.DictReader(stream))
    now=now_utc(); issues=health_issues(now,cfg,installation,scheduler,state,readiness)
    deliveries=send_health_notifications(issues,cfg,installation,folder=folder,now=now) if cfg['desktop_notifications'] and installation.get('provider')!='github-actions' else []
    health=dict(checked_at_utc=now.isoformat(), status='attention' if issues else 'healthy', issues=issues,
                notifications=deliveries, performance_evaluated=False)
    atomic_json(folder/'health.json',health); write_health_page(health,state,folder)
    return health


def run_child(command, log, timeout):
    with Path(log).open('a',encoding='utf-8') as stream:
        stream.write('\n['+now_utc().isoformat()+'] '+subprocess.list2cmdline(command)+'\n'); stream.flush()
        result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,
            env={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'})
    if result.returncode:
        raise RuntimeError('Subprocess exit '+str(result.returncode)+'; see '+str(log))


def operate_frozen(op, refresh_capture=False, at=None):
    """Continue labels after the last allowed origin; preserve evaluation gate."""
    current=at or now_utc()
    protocol=read_json(op.LIVE/'protocol.json')
    next_origin=current.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)
    if timestamp(protocol['start_utc'])<=next_origin<timestamp(protocol['end_utc_exclusive']):
        op.run(refresh_capture=refresh_capture)
        return
    with op.bound():
        if op.capture_needed(refresh_capture):
            op.snapshots.collect()
        op.legacy.labels()
        op.legacy.evaluate()
    atomic_json(op.OPS/'last_run.json', dict(at_utc=now_utc().isoformat(),
        result=dict(total_predictions=0,existing_predictions=0,status='LABELS_ONLY_OUTSIDE_FROZEN_ORIGIN_WINDOW'),
        scope='No new forecast origin outside frozen dates; actual labels and original fixed evaluation gate only.'))
    op.audit();op.verify_preserved();op.check_protected()


def run_pipeline():
    assert_writer_allowed()
    OUT.mkdir(parents=True,exist_ok=True);cfg=read_json(CONFIG)
    installation=read_json(OUT/'installation.json', {})
    executable=(installation.get('python_executable') or str(Path(sys.executable).with_name('python.exe'))) if os.name=='nt' else sys.executable
    started=now_utc(); stamp=started.strftime('%Y%m%dT%H%M%S%fZ')
    log=OUT/'logs'/(stamp+'.log'); log.parent.mkdir(parents=True,exist_ok=True)
    with process_lock(OUT/'worker.lock'):
        previous=read_json(OUT/'state.json',{})
        state=dict(status='running',started_at_utc=started.isoformat(),pid=os.getpid(),
                   last_success_utc=previous.get('last_success_utc'),log=log.relative_to(ROOT).as_posix(),attempt=0)
        atomic_json(OUT/'state.json',state)
        try:
            check_immutable(cfg)
            if started>=timestamp(cfg['stop_after_utc']):
                state.update(status='finished_schedule',finished_at_utc=now_utc().isoformat())
                atomic_json(OUT/'state.json',state)
                return 0
            refresh_scheduler_status()
            monitor(refresh=False)
            for attempt in range(1,cfg['attempts']+1):
                state.update(status='running',attempt=attempt);atomic_json(OUT/'state.json',state)
                try:
                    command=[executable,str(ROOT/'run_release.py'),'operate']
                    if needs_refresh(now_utc(),cfg):
                        command.append('--refresh-capture')
                    run_child(command,log,cfg['subprocess_timeout_seconds'])
                    if not capture_complete():
                        raise RuntimeError('Not all 17 sources succeeded; retry with a new immutable capture')
                    # Input ineligibility is not a software failure. No future
                    # outcomes or scores are read by this operational wrapper.
                    attempt_status=read_json(ROOT/'outputs/research/evidence_20261019/prospective/prospective_status.json')
                    state.update(status='succeeded',finished_at_utc=now_utc().isoformat(),
                                 last_success_utc=now_utc().isoformat(),
                                 forecast_statuses=[row['status'] for row in attempt_status['attempts']],
                                 forecasts_logged=attempt_status['total_predictions'],sources_ok=17)
                    if 'error' in state:
                        state['last_error']=state.pop('error')
                    atomic_json(OUT/'state.json',state)
                    monitor(refresh=False)
                    with process_lock(OUT/'operate.lock'):
                        run_child([executable,str(ROOT/'run_release.py'),'build'],log,cfg['subprocess_timeout_seconds'])
                    with (OUT/'runs.jsonl').open('a',encoding='utf-8') as stream:
                        stream.write(json.dumps(state,ensure_ascii=False)+'\n')
                    return 0
                except (OSError,RuntimeError,AssertionError,ValueError,subprocess.TimeoutExpired) as exc:
                    state.update(error=str(exc),last_error_utc=now_utc().isoformat(),last_success_utc=previous.get('last_success_utc'))
                    atomic_json(OUT/'state.json',state)
                    if attempt<cfg['attempts']:
                        time.sleep(cfg['retry_delay_seconds'])
                    else:
                        raise
        except Exception as exc:
            state.update(status='failed',error=str(exc),finished_at_utc=now_utc().isoformat(),last_success_utc=previous.get('last_success_utc'))
            atomic_json(OUT/'state.json',state)
            try:
                monitor(refresh=False)
            except Exception as monitor_error:
                with log.open('a',encoding='utf-8') as stream:
                    stream.write('\nMonitoring error: '+str(monitor_error)+'\n')
            return 1


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['run','monitor','status','test-notification'])
    args=parser.parse_args()
    if args.stage in ['run','monitor','test-notification']:
        try:
            assert_writer_allowed()
        except HostedAuthorityError as exc:
            if sys.stderr:
                print(str(exc),file=sys.stderr)
            return 78
    if args.stage=='run':
        try:
            return run_pipeline()
        except AlreadyRunningError:
            return 75
    if args.stage=='monitor':
        with process_lock(OUT/'monitor.lock'):
            health=monitor()
            installation=read_json(OUT/'installation.json',{})
            executable=(installation.get('python_executable') or str(Path(sys.executable).with_name('python.exe'))) if os.name=='nt' else sys.executable
            log=OUT/'logs'/(now_utc().strftime('%Y%m%dT%H%M%S%fZ')+'_monitor.log');log.parent.mkdir(parents=True,exist_ok=True)
            # Do not race the pipeline's rendering or write into its status.
            try:
                with process_lock(OUT/'operate.lock'):
                    run_child([executable,str(ROOT/'run_release.py'),'build'],log,300)
            except AlreadyRunningError:
                pass
            return 0 if health['status']=='healthy' else 1
    if args.stage=='test-notification':
        result=notify('Topic09 - Da bat tu dong', 'Pipeline chạy mỗi giờ phút 15; giám sát phút 45. Mô hình và protocol nghiên cứu được giữ nguyên.',read_json(OUT/'installation.json',{}))
        atomic_json(OUT/'notification_test.json',dict(at_utc=now_utc().isoformat(),**result))
        if sys.stdout:
            print(json.dumps(result,ensure_ascii=False))
        return 0 if result['submitted'] else 1
    if sys.stdout:
        print(json.dumps(automation_summary(),ensure_ascii=False,indent=2))
    return 0
