#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

TEXT_ENCODING = "utf-8"


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def report_dir() -> Path:
    xdg_state_home = os.environ.get("XDG_STATE_HOME")
    if xdg_state_home:
        root = Path(xdg_state_home) / "ralph-wiggum"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "ralph-wiggum"
    else:
        root = Path.home() / ".local" / "state" / "ralph-wiggum"
    return root / "benchmarks"


def now_stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_command(command: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )


def write_report(report: dict) -> Path:
    destination = report_dir()
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / "latest.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding=TEXT_ENCODING)
    return report_path


def smoke_suite() -> list[dict]:
    return [
        {
            "name": "template_render_build",
            "kind": "template",
            "template": "build",
            "prompt": "Add JWT authentication to the API.",
            "objective": "Ship a tested authentication change.",
            "done_when": "Tests pass and auth behavior is documented.",
            "contains": [
                "<promise>COMPLETE</promise>",
                "Objective:",
                "Done when:",
                "TDD loop:",
            ],
        },
        {
            "name": "queue_lifecycle",
            "kind": "queue",
            "prompt": "Fix the failing integration test.",
            "objective": "Get the integration test green.",
            "done_when": "The targeted test passes and the root cause is described.",
            "contains": [
                "Objective:",
                "Completion contract:",
                "Session:",
            ],
        },
    ]


def run_smoke_case(case: dict) -> dict:
    queue_script = skill_root() / "scripts" / "ralph_queue.py"
    with tempfile.TemporaryDirectory(prefix="ralph-bench-") as temp_dir:
        env = dict(os.environ)
        env["XDG_STATE_HOME"] = str(Path(temp_dir) / "state")
        base_command = [sys.executable, str(queue_script)]
        if case["kind"] == "template":
            result = run_command(
                base_command
                + [
                    "template",
                    "render",
                    case["template"],
                    "--prompt",
                    case["prompt"],
                    "--objective",
                    case["objective"],
                    "--done-when",
                    case["done_when"],
                ],
                env=env,
            )
        else:
            start = run_command(
                base_command
                + [
                    "loop",
                    "--template",
                    "build",
                    "--prompt",
                    case["prompt"],
                    "--objective",
                    case["objective"],
                    "--done-when",
                    case["done_when"],
                    "--max-iterations",
                    "2",
                    "--json",
                ],
                env=env,
            )
            emit = run_command(base_command + ["next"], env=env)
            status = run_command(base_command + ["status", "--json"], env=env)
            combined_output = "\n".join([start.stdout, emit.stdout, status.stdout])
            result = subprocess.CompletedProcess(
                args=[],
                returncode=max(start.returncode, emit.returncode, status.returncode),
                stdout=combined_output,
                stderr="\n".join(filter(None, [start.stderr, emit.stderr, status.stderr])),
            )
        checks = {needle: needle in result.stdout for needle in case["contains"]}
        passed = result.returncode == 0 and all(checks.values())
        return {
            "name": case["name"],
            "passed": passed,
            "returncode": result.returncode,
            "checks": checks,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }


def cmd_smoke(args: argparse.Namespace) -> int:
    results = [run_smoke_case(case) for case in smoke_suite()]
    report = {
        "suite": "smoke",
        "generated_at": now_stamp(),
        "passed": sum(1 for result in results if result["passed"]),
        "total": len(results),
        "results": results,
    }
    report_path = write_report(report)
    if args.json:
        print(json.dumps({"report_path": str(report_path), **report}, indent=2))
        return 0 if report["passed"] == report["total"] else 1
    print(f"Smoke suite: {report['passed']}/{report['total']} passed")
    print(f"Report: {report_path}")
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"- {status} {result['name']}")
    return 0 if report["passed"] == report["total"] else 1


def cmd_harbor(args: argparse.Namespace) -> int:
    harbor = shutil.which("harbor")
    if not harbor:
        print("error: harbor is not installed or not on PATH", file=sys.stderr)
        return 2
    dataset = Path(args.dataset).expanduser().resolve()
    commands = [
        [harbor, "tasks", "check", "--dataset", str(dataset)],
    ]
    if not args.check_only:
        commands.append([harbor, "run", "--dataset", str(dataset), "--agent", args.agent])
    completed = []
    for command in commands:
        result = run_command(command)
        completed.append(
            {
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        )
        if result.returncode != 0:
            break
    report = {
        "suite": "harbor",
        "generated_at": now_stamp(),
        "dataset": str(dataset),
        "agent": args.agent,
        "commands": completed,
    }
    report_path = write_report(report)
    exit_code = 0 if all(item["returncode"] == 0 for item in completed) else 1
    if args.json:
        print(json.dumps({"report_path": str(report_path), **report}, indent=2))
        return exit_code
    print(f"Harbor report: {report_path}")
    for item in completed:
        joined = " ".join(item["command"])
        print(f"- {item['returncode']} {joined}")
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark Ralph Wiggum loop quality")
    subparsers = parser.add_subparsers(dest="command", required=True)

    smoke_parser = subparsers.add_parser("smoke", help="Run local Ralph regression smoke tests")
    smoke_parser.add_argument("--json", action="store_true", help="JSON output")
    smoke_parser.set_defaults(func=cmd_smoke)

    harbor_parser = subparsers.add_parser("harbor", help="Run optional Harbor / SkillsBench commands")
    harbor_parser.add_argument("--dataset", required=True, help="Path to a Harbor dataset")
    harbor_parser.add_argument("--agent", default="codex", help="Agent name passed to harbor run")
    harbor_parser.add_argument("--check-only", action="store_true", help="Only validate the dataset")
    harbor_parser.add_argument("--json", action="store_true", help="JSON output")
    harbor_parser.set_defaults(func=cmd_harbor)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
