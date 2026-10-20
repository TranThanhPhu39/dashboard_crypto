"""Verify the real local installation after both Windows tasks have completed."""
from pathlib import Path
import sys
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.automation_runtime import (OUT,CONFIG,POWERSHELL,read_json,atomic_json,now_utc,
                                  check_immutable,automation_summary,write_health_page,digest)

subprocess.run([str(POWERSHELL),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-WindowStyle','Hidden',
    '-File',str(ROOT/'tools/manage_topic09_automation.ps1'),'-Action','Status'],check=True,capture_output=True)
cfg=read_json(CONFIG);scheduler=read_json(OUT/'scheduler_status.json');installation=read_json(OUT/'installation.json')
state=read_json(OUT/'state.json');health=read_json(OUT/'health.json');guards=read_json(OUT/'guard_validation.json')
notice=read_json(OUT/'notification_test.json');pointer=read_json(ROOT/'outputs/research/evidence_20261019/prospective/latest_capture.json')
check_immutable(cfg)
checks=dict(two_owned_tasks_enabled=automation_summary()['installed'],
            real_pipeline_and_monitor_exit_zero=all(task['last_task_result']==0 and task['state']=='Ready' for task in scheduler['tasks']),
            pipeline_completed_with_real_sources=state['status']=='succeeded' and state['sources_ok']==17,
            source_capture_currently_complete=pointer['sources_ok']==pointer['sources_total']==17,
            healthy_no_open_incidents=health['status']=='healthy' and not health['issues'],
            windows_notification_submission_test=notice['submitted'] is True,
            operational_guards_passed=guards['passed'] is True and guards['tests']==46,
            installation_uses_current_authorized_config=installation['config_sha256']==digest(CONFIG),
            frozen_protocol_inventory_hashes_unchanged=True, no_password_stored=installation['password_stored'] is False)
ns={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'}
for role in ['pipeline','monitor']:
    tree=ET.parse(OUT/(role+'_task.xml'))
    get=lambda name:tree.findtext('.//t:'+name,namespaces=ns)
    task=next(row for row in scheduler['tasks'] if row['role']==role)
    checks[role+'_schedule_safety']=(tree.findtext('.//t:TimeTrigger/t:Repetition/t:Interval',namespaces=ns)=='PT1H' and get('LogonType')=='InteractiveToken'
        and task['run_level']=='Limited' and task['logon_type']=='Interactive' and get('RunLevel') in (None,'LeastPrivilege') and get('StartWhenAvailable')=='true'
        and get('WakeToRun')=='true' and get('MultipleInstancesPolicy')=='IgnoreNew')
assert all(checks.values()),checks
write_health_page(health,state)
atomic_json(OUT/'integration_validation.json',dict(checked_at_utc=now_utc().isoformat(),checks=checks,
    passed=sum(checks.values()),total=len(checks),source_manifest=pointer['manifest'],source_manifest_sha256=pointer['sha256'],
    performance_claim=False,scope='Real installed Windows tasks, actual source retry/run, notification submission; not predictive skill'))
print('Installed automation checks:',len(checks),'passed. Both Windows tasks returned 0.')
