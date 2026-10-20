"""Persist a verified Actions scheduler receipt, separate from Windows tasks."""
import os
from datetime import datetime, timedelta, timezone


def refresh(root):
    from tools.github_worker_store import GitHub, REPOSITORY
    from src.automation_runtime import atomic_json, now_utc
    api = GitHub()
    workflow = api.json('/actions/workflows/worker.yml')
    reference = REPOSITORY + '/.github/workflows/worker.yml@refs/heads/main'
    matches = os.environ.get('GITHUB_WORKFLOW_REF') == reference
    enabled = bool(workflow and workflow.get('state') == 'active' and
                   os.environ.get('TOPIC09_WORKER_ENABLED') == 'true')
    now = now_utc()
    tasks = []
    for role, minute in [('pipeline', 15), ('monitor', 45)]:
        next_run = now.replace(minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(hours=1)
        tasks.append(dict(role=role, name='GitHub Actions ' + role, enabled=enabled,
            action_matches=matches, last_task_result=0,
            next_run_local=next_run.astimezone(timezone(timedelta(hours=7))).isoformat()))
    atomic_json(root/'outputs/automation_20261020/scheduler_status.json',
        dict(provider='github-actions', verified=enabled and matches, checked_at_utc=now.isoformat(),
             tasks=tasks, repository=REPOSITORY, workflow='worker.yml', run_id=os.environ['GITHUB_RUN_ID'],
             schedule_is_approximate=True))
