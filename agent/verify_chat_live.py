"""Read-only deployment checks: health + rejected identities only; zero model calls."""
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

import httpx


def main() -> int:
    checks = []
    try:
        with httpx.Client(trust_env=False, timeout=15) as client:
            for base in ("http://127.0.0.1:8002", "http://127.0.0.1:5173/agent-api"):
                response = client.get(base + "/health")
                checks.append({"target": base, "check": "health", "passed": response.status_code == 200 and response.json().get("ready") is True})
                for name, headers in (("anonymous_denied", {}), ("invalid_token_denied", {"Authorization": "Bearer intentionally-invalid-agent-test-token"})):
                    response = client.post(base + "/chat", headers=headers,
                                           json={"question": "只读部署检查，不应进入模型", "request_id": str(uuid4())})
                    checks.append({"target": base, "check": name, "passed": response.status_code == 401})
    except Exception:
        checks.append({"check": "connection_or_format", "passed": False})
    report = {"at": datetime.now(timezone.utc).isoformat(), "passed": len(checks) == 6 and all(row["passed"] for row in checks),
              "checks": checks, "paid_model_calls": 0, "real_credentials_used": False, "business_writes": 0}
    target = Path(__file__).resolve().parent.parent / "docs/verification/agent-chat-api.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
