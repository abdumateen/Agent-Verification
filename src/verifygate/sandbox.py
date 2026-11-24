"""Run snapshot checks in disposable, restricted Docker containers."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
import secrets


MAX_LOG_BYTES = 64 * 1024
MAX_REPORT_BYTES = 64 * 1024


def _bind_path(path: Path) -> str:
    return path.resolve().as_posix()


def _parse_control_record(stdout: str, nonce: str) -> dict:
    """Accept exactly one, otherwise-empty trusted control-channel record."""
    start = f'VERIFYGATE_RESULT<{nonce}>:'
    end = f':VERIFYGATE_RESULT<{nonce}>'
    match = re.fullmatch(r'\s*' + re.escape(start) + r'(.*?)' + re.escape(end) + r'\s*', stdout, re.DOTALL)
    if not match:
        raise ValueError('expected exactly one well-formed control record')
    raw = match.group(1).encode('utf-8')
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError('oversized unittest report')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate report field')
            value[key] = item
        return value
    report = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
    if not isinstance(report, dict) or set(report) != {'tests_run', 'failures', 'errors'}:
        raise ValueError('invalid report fields')
    count, failures, errors = (report[key] for key in ('tests_run', 'failures', 'errors'))
    if any(type(value) is not int or value < 0 for value in (count, failures, errors)) or failures + errors > count:
        raise ValueError('invalid report counts')
    return report


def _execute(argv, timeout):
    """Drain both pipes concurrently, retaining only bounded prefixes."""
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    buffers = [bytearray(), bytearray()]
    truncated = [False, False]

    def drain(pipe, index):
        try:
            while chunk := pipe.read(8192):
                remaining = max(0, MAX_LOG_BYTES - len(buffers[index]))
                buffers[index].extend(chunk[:remaining])
                truncated[index] |= len(chunk) > remaining
        finally:
            pipe.close()

    threads = [threading.Thread(target=drain, args=(pipe, i), daemon=True)
               for i, pipe in enumerate((process.stdout, process.stderr))]
    for thread in threads:
        thread.start()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise
    finally:
        for thread in threads:
            thread.join()
    return (process.returncode, *(bytes(part).decode('utf-8', errors='replace')
                                  for part in buffers), any(truncated))


def run_checks(snapshot_dir: Path, policy: dict, *, snapshot_hash=None,
               policy_hash=None, execution_provenance='live_docker', acceptance=None) -> list[dict]:
    results = []
    for check in policy['checks']:
        kind = check['type']
        nonce = secrets.token_hex(24) if kind in ('unittest', 'acceptance') else None
        command = (list(check['argv']) if kind == 'command' else
                   ['python', '-I', '/opt/app/src/verifygate/test_harness.py', '--nonce', nonce] +
                   (['--start-dir', '/opt/app/acceptance'] if kind == 'acceptance' else []))
        started = datetime.now(timezone.utc)
        tick = time.monotonic()
        result = {'id': check['id'], 'status': 'inconclusive', 'command': command,
                  'exit_code': None, 'tests_run': None, 'output': '', 'stdout': '',
                  'stderr': '', 'output_truncated': False, 'runner': 'docker',
                  'started_at': started.isoformat(), 'ended_at': None,
                  'duration_seconds': None, 'report_sha256': None, 'report_size': None,
                  'provenance': execution_provenance,
                  'report_provenance': 'trusted_harness_stdout' if kind in ('unittest', 'acceptance') else None,
                   'test_source': ('trusted_acceptance' if kind == 'acceptance' else check.get('test_source', 'candidate')) if kind in ('unittest', 'acceptance') else None}
        if kind == 'acceptance' and acceptance:
            result.update(acceptance_suite_id=acceptance['suite_id'], acceptance_suite_version=acceptance['version'], acceptance_fingerprint=acceptance['fingerprint'])
        if snapshot_hash is not None:
            result['snapshot_hash'] = snapshot_hash
        if policy_hash is not None:
            result['policy_hash'] = policy_hash
        try:
            with tempfile.TemporaryDirectory(prefix='verifygate-results-') as directory:
                cidfile = Path(directory) / 'container-id'
                argv = ['docker', 'run', '--rm', '--cidfile', _bind_path(cidfile),
                        '--network', 'none', '--read-only',
                        '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                        '--pids-limit', '128', '--memory',
                        f"{check.get('memory', policy.get('memory', 512))}m",
                        '--cpus', str(check.get('cpus', policy.get('cpus', 1))),
                        '--user', '65534:65534', '--tmpfs', '/tmp:rw,nosuid,nodev,size=64m',
                        '--mount', f'type=bind,source={_bind_path(snapshot_dir)},target=/workspace,readonly',
                        *(['--mount', f"type=bind,source={_bind_path(Path(acceptance['host_path']))},target=/opt/app/acceptance,readonly"] if kind == 'acceptance' and acceptance else []),
                         '--workdir', '/workspace', '--env',
                         ('PYTHONPATH=/workspace:/opt/app/src' if kind == 'acceptance'
                          else 'PYTHONPATH=/opt/app/src')]
                argv += [policy['image'], *command]
                try:
                    code, stdout, stderr, truncated = _execute(
                        argv, check.get('timeout', policy.get('timeout', 180)))
                except (OSError, subprocess.TimeoutExpired) as exc:
                    result['output'] = str(exc)[:MAX_LOG_BYTES]
                    if isinstance(exc, subprocess.TimeoutExpired) and cidfile.exists():
                        container_id = cidfile.read_text(encoding='ascii').strip()
                        if re.fullmatch(r'[0-9a-f]{64}', container_id):
                            try:
                                subprocess.run(['docker', 'rm', '-f', container_id],
                                               capture_output=True, timeout=10, check=True)
                            except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as cleanup_error:
                                result['output'] += f'\nContainer cleanup failed: {type(cleanup_error).__name__}'
                    continue
                result.update(exit_code=code, stdout=stdout, stderr=stderr,
                              output_truncated=truncated,
                              output=(stdout + stderr)[:MAX_LOG_BYTES])
                result['output_truncated'] |= len((stdout + stderr).encode('utf-8')) > MAX_LOG_BYTES
                if code in (125, 126, 127):
                    continue
                if kind == 'command':
                    result['status'] = 'passed' if code == 0 else 'failed'
                    continue
                try:
                    assert nonce is not None
                    report = _parse_control_record(stdout, nonce)
                    count, failures, errors = (report[key] for key in ('tests_run', 'failures', 'errors'))
                    if (code == 0) != (count > 0 and failures == errors == 0):
                        # Zero-test runs conventionally exit 1.
                        if count != 0 or code == 0:
                            raise ValueError('report contradicts exit code')
                    canonical = json.dumps({'tests_run': count, 'failures': failures, 'errors': errors},
                                           sort_keys=True, separators=(',', ':')).encode('utf-8')
                    result['report_sha256'] = hashlib.sha256(canonical).hexdigest()
                    result['report_size'] = len(canonical)
                except (OSError, UnicodeError, ValueError, TypeError) as exc:
                    result['output'] = (result['output'] + f'\nMissing or invalid unittest report: {exc}')[:MAX_LOG_BYTES]
                else:
                    result['tests_run'] = count
                    result['status'] = 'failed' if count == 0 or count < check['minimum_tests'] or failures or errors else 'passed'
        except OSError as exc:
            result['status'] = 'inconclusive'
            result['output'] = (result['output'] + f'\nEvidence workspace cleanup failed: {exc}')[:MAX_LOG_BYTES]
        finally:
            result['ended_at'] = datetime.now(timezone.utc).isoformat()
            result['duration_seconds'] = time.monotonic() - tick
            results.append(result)
    return results
