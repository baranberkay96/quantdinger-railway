#!/usr/local/bin/python3
"""Start and pre-deploy wrapper for QuantDinger's backend image on Railway.

Usage: railway-quantdinger <mode>

Pre-deploy modes (run before a deployment starts, with retries):
  migrate        python -m app.commands.migrate (upstream's one-shot "migration" service)
  kafka-topics   python -m app.commands.kafka_topics (upstream's one-shot "kafka-init" service)

Process roles (the long-running services of upstream's docker-compose.yml):
  api, trading, scheduler, kafka-audit, strategy-dispatcher, strategy-evaluator,
  celery, celery-backtest, celery-beat

For a process role the wrapper
  1. prepares the dotenv file the app reads (QUANTDINGER_ENV_FILE, default /app/.env):
     created from the image's env.example, new keys of a newer env.example appended, and
     every non-empty Railway variable whose key is in that file written into it. The app
     reads feature switches for the UI from this file and reloads it over the process
     environment after a Settings save, so it must hold the real values, not examples;
  2. removes empty Railway variables whose key is in that file, so values saved on the
     Settings page (Backend volume) still apply;
  3. checks the secrets and the bootstrap administrator (fails closed only when unsafe);
  4. caps native thread pools to the service's CPU quota;
  5. waits for the database schema (workers only; the Backend's pre-deploy migrates);
  6. execs upstream's /usr/local/bin/docker-entrypoint.sh with compose's command.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import time

APP_DIR = "/app"
ENV_TEMPLATE = "/app/env.example"
DEFAULT_ENV_FILE = "/app/.env"
ENTRYPOINT = "/usr/local/bin/docker-entrypoint.sh"
CPU_MAX_FILE = "/sys/fs/cgroup/cpu.max"
CELERY_APP = "app.celery_app:celery_app"
MIGRATION_DIR = "/app/migrations"
# Ledger rows written by app.utils.db._apply_init_sql: the first and the last component.
SCHEMA_MARKERS = {
    "schema-init": "init.sql",
    "strategy-v2-templates": "strategy_v2_templates.sql",
}
# Read by the UI from the dotenv file; a missing key there means "enabled".
ALWAYS_WRITE = (
    "ENABLE_REGISTRATION",
    "LIVE_TRADING_ENABLED",
    "AGENT_LIVE_TRADING_ENABLED",
    "BROKER_ACCOUNTS_ENABLED",
    "AGENT_GATEWAY_ENABLED",
    "BILLING_ENABLED",
    "MARKETPLACE_ENABLED",
)
SECRET_KEYS = ("SECRET_KEY", "CREDENTIAL_ENCRYPTION_KEY")
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_MAX_THREADS")
KEY_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
ADMIN_USER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,49}$")
DEFAULT_ADMIN_USER = "admin"

ROLES = {
    "api": "api",
    "trading": "trading",
    "scheduler": "scheduler",
    "kafka-audit": "kafka-audit",
    "strategy-dispatcher": "strategy-dispatcher",
    "strategy-evaluator": "strategy-evaluator",
    "celery": "celery",
    "celery-backtest": "celery",
    "celery-beat": "celery",
}


def log(message: str) -> None:
    print(f"[railway] {message}", file=sys.stderr, flush=True)


def int_setting(env: dict, name: str, default: int, minimum: int = 1) -> int:
    raw = (env.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        log(f"WARNING: {name}={raw!r} is not a number; using {default}")
        return default
    if value < minimum:
        log(f"WARNING: {name}={value} is below {minimum}; using {default}")
        return default
    return value


def role_command(mode: str, env: dict) -> list[str]:
    commands = {
        "api": ["gunicorn", "-c", "gunicorn_config.py", "run:app"],
        "trading": ["python", "-m", "app.commands.trading_worker"],
        "scheduler": ["python", "-m", "app.commands.scheduler"],
        "kafka-audit": ["python", "-m", "app.commands.kafka_audit_worker"],
        "strategy-dispatcher": ["python", "-m", "app.commands.strategy_dispatcher_worker"],
        "strategy-evaluator": ["python", "-m", "app.commands.strategy_evaluator_worker"],
    }
    if mode in commands:
        return commands[mode]
    if mode == "celery":
        concurrency = int_setting(env, "CELERY_CONCURRENCY", 2)
        return ["celery", "-A", CELERY_APP, "worker", "--loglevel=INFO", "-Q", "ai,maintenance",
                f"--concurrency={concurrency}"]
    if mode == "celery-backtest":
        concurrency = int_setting(env, "CELERY_BACKTEST_CONCURRENCY", 1)
        memory_kb = int_setting(env, "CELERY_BACKTEST_MAX_MEMORY_KB", 1572864, minimum=65536)
        return ["celery", "-A", CELERY_APP, "worker", "--loglevel=INFO", "-Q", "backtest",
                f"--concurrency={concurrency}", "--max-tasks-per-child=1",
                f"--max-memory-per-child={memory_kb}"]
    if mode == "celery-beat":
        return ["celery", "-A", CELERY_APP, "beat", "--loglevel=INFO",
                "--schedule=/tmp/celerybeat-schedule"]
    raise ValueError(f"unknown mode {mode!r}")


# ---------------------------------------------------------------- dotenv file

def format_env_line(key: str, value: str) -> str:
    """Same quoting as upstream's app/services/settings/env_file.py."""
    text = str(value)
    if re.search(r"[\s#'\"\\]", text):
        escaped = (text.replace("\\", "\\\\").replace('"', '\\"')
                   .replace("\r", "\\r").replace("\n", "\\n"))
        return f'{key}="{escaped}"\n'
    return f"{key}={text}\n"


def read_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    return lines


def line_key(line: str) -> str | None:
    if line.lstrip().startswith("#"):
        return None
    match = KEY_RE.match(line)
    return match.group(1) if match else None


def merge_env_file(lines: list[str], template_lines: list[str], env: dict) -> tuple[list[str], dict]:
    """Return the new file lines and a summary of what changed."""
    present = {key for key in map(line_key, lines) if key}
    out = list(lines)

    added_from_template = []
    for line in template_lines:
        key = line_key(line)
        if key and key not in present:
            if not added_from_template:
                out.append("\n# Added from the image's env.example (newer release)\n")
            out.append(line)
            present.add(key)
            added_from_template.append(key)

    managed = {key: value for key, value in env.items()
               if key in present and str(value).strip() != ""}
    synced = []
    for index, line in enumerate(out):
        key = line_key(line)
        if key in managed:
            new_line = format_env_line(key, managed[key])
            if new_line != line:
                out[index] = new_line
                synced.append(key)

    appended = []
    for key in ALWAYS_WRITE:
        value = str(env.get(key) or "").strip()
        if key not in present and value:
            if not appended:
                out.append("\n# Added by the Railway template (read by the web UI)\n")
            out.append(format_env_line(key, value))
            present.add(key)
            appended.append(key)

    summary = {"from_template": added_from_template, "synced": sorted(set(synced)),
               "appended": appended, "keys": present}
    return out, summary


def prepare_env_file(env: dict) -> set[str]:
    path = (env.get("QUANTDINGER_ENV_FILE") or "").strip() or DEFAULT_ENV_FILE
    template_lines = read_lines(ENV_TEMPLATE) if os.path.isfile(ENV_TEMPLATE) else []
    if not template_lines:
        log(f"WARNING: {ENV_TEMPLATE} not found; the env file starts empty")

    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    created = not os.path.isfile(path)
    lines = list(template_lines) if created else read_lines(path)
    new_lines, summary = merge_env_file(lines, template_lines, env)

    if created or new_lines != lines:
        tmp_path = f"{path}.railway-tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.writelines(new_lines)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    else:
        os.chmod(path, 0o600)

    if os.path.abspath(path) != os.path.abspath(DEFAULT_ENV_FILE):
        if os.path.islink(DEFAULT_ENV_FILE) or os.path.isfile(DEFAULT_ENV_FILE):
            os.remove(DEFAULT_ENV_FILE)
        os.symlink(path, DEFAULT_ENV_FILE)

    log(f"env file {path}: {'created from env.example, ' if created else ''}"
        f"{len(summary['synced'])} value(s) set from Railway variables"
        + (f", {len(summary['from_template'])} new key(s) from env.example" if summary["from_template"] else "")
        + (f", added {', '.join(summary['appended'])}" if summary["appended"] else ""))
    return summary["keys"]


def drop_empty_variables(env: dict, file_keys: set[str]) -> list[str]:
    """Empty Railway variables would hide the file's value (load_dotenv override=False)."""
    dropped = sorted(key for key in file_keys
                     if key in env and str(env[key]).strip() == "" and key not in SECRET_KEYS
                     and key != "ADMIN_PASSWORD")
    for key in dropped:
        del env[key]
    return dropped


# ---------------------------------------------------------------- checks

def check_secrets(env: dict) -> bool:
    ok = True
    for key in SECRET_KEYS:
        value = str(env.get(key) or "").strip()
        if len(value) < 32:
            log(f"ERROR: {key} must be at least 32 characters (it is generated by the template; "
                "restore it in Railway -> Backend -> Variables). Refusing to start with a per-container random key.")
            ok = False
    return ok


def check_admin(env: dict) -> bool:
    user = str(env.get("ADMIN_USER") or "").strip()
    if not ADMIN_USER_RE.match(user):
        log(f"WARNING: ADMIN_USER {user!r} is not 3-50 letters, digits or underscores starting with a letter; "
            f"using {DEFAULT_ADMIN_USER!r}")
        env["ADMIN_USER"] = DEFAULT_ADMIN_USER
    else:
        env["ADMIN_USER"] = user
    password = str(env.get("ADMIN_PASSWORD") or "")
    if len(password) < 8 or len(password.encode("utf-8")) > 72 or password == "123456":
        log("ERROR: ADMIN_PASSWORD must be 8-72 bytes and not the upstream default. "
            "It creates the first administrator; set it in Railway -> Backend -> Variables.")
        return False
    return True


def cpu_quota(path: str = CPU_MAX_FILE) -> int | None:
    try:
        with open(path, encoding="ascii") as handle:
            quota, period = handle.read().split()[:2]
        if quota == "max":
            return None
        return max(1, -(-int(quota) // int(period)))
    except (OSError, ValueError):
        return None


def cap_threads(env: dict) -> int:
    cap = int_setting(env, "QD_THREAD_CAP", 4)
    threads = max(1, min(cpu_quota() or os.cpu_count() or 1, cap))
    for key in THREAD_VARS:
        if not str(env.get(key) or "").strip():
            env[key] = str(threads)
    return threads


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_schema() -> dict:
    expected = {}
    for name, filename in SCHEMA_MARKERS.items():
        path = os.path.join(MIGRATION_DIR, filename)
        if os.path.isfile(path):
            expected[name] = file_sha256(path)
    return expected


def schema_status(dsn: str, expected: dict) -> str | None:
    """None when the migration ledger matches this image; otherwise the reason."""
    import psycopg2  # in the image (requirements.lock)

    conn = psycopg2.connect(dsn, connect_timeout=5)
    try:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('qd_bootstrap_migrations')")
        if cur.fetchone()[0] is None:
            return "migration ledger not created yet"
        cur.execute("SELECT name, checksum FROM qd_bootstrap_migrations WHERE name = ANY(%s)",
                    (list(expected),))
        applied = dict(cur.fetchall())
    finally:
        conn.close()
    pending = [name for name, checksum in expected.items() if applied.get(name) != checksum]
    return f"waiting for {', '.join(pending)}" if pending else None


def wait_for_schema(env: dict, sleep=time.sleep, now=time.monotonic) -> bool:
    dsn = str(env.get("DATABASE_URL") or "").strip()
    expected = expected_schema()
    if not dsn or not expected:
        log("WARNING: DATABASE_URL or migration files missing; not waiting for the schema")
        return False
    limit = int_setting(env, "QD_SCHEMA_WAIT_SECONDS", 900, minimum=0)
    deadline = now() + limit
    attempt = 0
    while True:
        attempt += 1
        try:
            reason = schema_status(dsn, expected)
        except Exception as exc:  # database still starting
            reason = f"database not reachable ({type(exc).__name__})"
        if reason is None:
            log("schema: current (migration ledger matches this image)")
            return True
        if now() >= deadline:
            log(f"WARNING: schema not current after {limit}s ({reason}); starting anyway")
            return False
        if attempt == 1 or attempt % 6 == 0:
            log(f"schema: {reason}; Backend's pre-deploy migration runs first, retrying")
        sleep(10)


# ---------------------------------------------------------------- modes

def run_with_retries(cmd: list[str], env: dict, label: str, sleep=time.sleep) -> int:
    attempts = int_setting(env, "QD_PREDEPLOY_ATTEMPTS", 60)
    delay = int_setting(env, "QD_PREDEPLOY_DELAY_SECONDS", 10)
    for attempt in range(1, attempts + 1):
        code = subprocess.call(cmd, cwd=APP_DIR, env=env)
        if code == 0:
            log(f"{label}: done (attempt {attempt})")
            return 0
        if attempt == attempts:
            log(f"{label}: failed {attempts} times (exit {code}), giving up")
            return code or 1
        log(f"{label}: attempt {attempt} failed (exit {code}; dependency still starting?), retrying in {delay}s")
        sleep(delay)
    return 1


def prepare_metrics_dir(env: dict) -> None:
    # The image's entrypoint creates this directory; pre-deploy commands run without
    # it, and prometheus_client's multiprocess mode fails every DB pool without it.
    metrics_dir = str(env.get("PROMETHEUS_MULTIPROC_DIR") or "").strip()
    if metrics_dir:
        os.makedirs(metrics_dir, exist_ok=True)


def predeploy(mode: str, env: dict) -> int:
    prepare_metrics_dir(env)
    if mode == "migrate":
        env.update({"SKIP_AUTO_MIGRATE": "false", "DB_POOL_MIN": "1", "DB_POOL_MAX": "2",
                    "DB_APPLICATION_NAME": "quantdinger-migration"})
        return run_with_retries([sys.executable, "-m", "app.commands.migrate"], env, "migration")
    if not str(env.get("KAFKA_BOOTSTRAP_SERVERS") or "").strip():
        log("kafka-topics: KAFKA_BOOTSTRAP_SERVERS is empty")
        return 1
    env.setdefault("KAFKA_ADMIN_CLIENT_ID", "quantdinger-topic-init")
    return run_with_retries([sys.executable, "-m", "app.commands.kafka_topics"], env, "kafka topics")


def start(mode: str, env: dict) -> int:
    role = ROLES[mode]
    configured = str(env.get("QD_PROCESS_ROLE") or "").strip()
    if configured and configured != role:
        log(f"WARNING: QD_PROCESS_ROLE={configured!r} does not match this service; using {role!r}")
    env["QD_PROCESS_ROLE"] = role

    if not check_secrets(env):
        return 1
    if mode == "api" and not check_admin(env):
        return 1

    file_keys = prepare_env_file(env)
    dropped = drop_empty_variables(env, file_keys)
    if dropped:
        log(f"empty variables left to the env file: {', '.join(dropped)}")
    threads = cap_threads(env)
    log(f"role {role}: native thread pools capped at {threads}")

    if mode != "api":
        wait_for_schema(env)

    cmd = role_command(mode, env)
    target = ENTRYPOINT if os.path.isfile(ENTRYPOINT) else shutil.which(cmd[0])
    argv = [ENTRYPOINT, *cmd] if target == ENTRYPOINT else cmd
    log(f"exec {' '.join(argv)}")
    os.chdir(APP_DIR)
    os.execve(target, argv, env)
    return 1  # not reached


def self_test() -> int:
    problems = [path for path in (ENTRYPOINT, ENV_TEMPLATE, *(
        os.path.join(MIGRATION_DIR, name) for name in SCHEMA_MARKERS.values())) if not os.path.isfile(path)]
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        problems.append("python module psycopg2")
    for module in ("app.commands.migrate", "app.commands.kafka_topics", "app.commands.trading_worker",
                   "app.commands.scheduler", "app.commands.kafka_audit_worker",
                   "app.commands.strategy_dispatcher_worker", "app.commands.strategy_evaluator_worker"):
        if not os.path.isfile(os.path.join(APP_DIR, *module.split(".")) + ".py"):
            problems.append(module)
    if problems:
        log("self-test failed, missing: " + ", ".join(problems))
        return 1
    log("self-test ok")
    return 0


def main(argv: list[str]) -> int:
    args = list(argv[1:])
    if args and os.path.basename(args[0]) == "railway-quantdinger":
        args = args[1:]  # tolerate the wrapper path passed twice (ENTRYPOINT + start command)
    mode = args[0] if args else "api"
    if mode == "--self-test":
        return self_test()
    env = dict(os.environ)
    if mode in ("migrate", "kafka-topics"):
        return predeploy(mode, env)
    if mode in ROLES:
        return start(mode, env)
    log(f"unknown mode {mode!r}; expected migrate, kafka-topics or one of {', '.join(ROLES)}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
