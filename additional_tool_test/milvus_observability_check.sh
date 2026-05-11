#!/usr/bin/env bash
set -euo pipefail

# Milvus lightweight observability check:
# - verifies compose service states
# - verifies critical ports
# - verifies pymilvus connectivity and collection listing
# Output: one-line status for crontab/systemd integration.

MILVUS_DIR="/mnt/data/milvus"
PROJECT_DIR="/home/bupt/Server_Project_ZH"
PYTHON_BIN="/home/bupt/Server_Project_ZH/venv/bin/python"
LOG_FILE="${PROJECT_DIR}/logs/milvus_observability.log"
RETRY_COUNT="${RETRY_COUNT:-3}"
RETRY_INTERVAL="${RETRY_INTERVAL:-5}"

mkdir -p "${PROJECT_DIR}/logs"

timestamp="$(date '+%Y-%m-%d %H:%M:%S')"

fail() {
  local reason="$1"
  echo "${timestamp} [ALERT] ${reason}" | tee -a "${LOG_FILE}"
  exit 1
}

ok() {
  local msg="$1"
  echo "${timestamp} [OK] ${msg}" | tee -a "${LOG_FILE}"
}

if ! command -v docker >/dev/null 2>&1; then
  fail "docker command not found"
fi

compose_cmd() {
  if docker compose ps -a >/dev/null 2>&1; then
    docker compose "$@"
    return
  fi

  if sudo -n docker compose ps -a >/dev/null 2>&1; then
    sudo -n docker compose "$@"
    return
  fi

  fail "docker compose needs privilege; run as root or configure passwordless sudo for docker"
}

if ! cd "${MILVUS_DIR}"; then
  fail "cannot enter ${MILVUS_DIR}"
fi

# Check service state with short retries to absorb restart windows.
check_services_once() {
  local running
  running="$(compose_cmd ps --status running --services 2>/dev/null || true)"
  for svc in etcd minio standalone; do
    if ! echo "${running}" | grep -qx "${svc}"; then
      return 1
    fi
  done
  return 0
}

service_ok=0
for _ in $(seq 1 "${RETRY_COUNT}"); do
  if check_services_once; then
    service_ok=1
    break
  fi
  sleep "${RETRY_INTERVAL}"
done

if [[ "${service_ok}" -ne 1 ]]; then
  fail "service check failed after retries: etcd/minio/standalone not all running"
fi

# Check ports
if ! ss -ltn | grep -Eq ':19530|:9091'; then
  fail "Milvus ports 19530/9091 are not listening"
fi

# Check pymilvus from project runtime
if [[ ! -x "${PYTHON_BIN}" ]]; then
  fail "python runtime not found: ${PYTHON_BIN}"
fi

conn_out="$(${PYTHON_BIN} - <<'PY'
from pymilvus import connections, utility
try:
    connections.connect(alias='default', host='127.0.0.1', port='19530')
    cols = utility.list_collections()
    print('ok collections=' + str(len(cols)))
except Exception as exc:
    print('error ' + str(exc))
    raise
finally:
    try:
        connections.disconnect('default')
    except Exception:
        pass
PY
)" || fail "pymilvus connectivity check failed"

ok "${conn_out}"
