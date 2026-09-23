"""Run, verify, serve and export local memory experiments."""

import argparse
import shutil
import sys
from datetime import UTC, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

from .evaluator_exploits import EXPERIMENT
from .runner import ROOT, build_bundle, export, read_json, verify, verify_source

PUBLIC_DIRS = ("web", "artifacts", "reports", "experiments")


def stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def export_site(release: Path, output: Path, campaign_release: Path) -> None:
    """Copy verified evidence and the three browser pages into a portable static directory."""
    verify(release)
    verify(campaign_release)
    if campaign_release.name == release.name:
        raise ValueError("Memory and campaign releases need distinct directory names")
    pages = {
        "index.html": ("../artifacts/agent-study-03/", campaign_release),
        "memory.html": ("../artifacts/article-01.6/", release),
    }
    for name, (prefix, _) in pages.items():
        if prefix not in (ROOT / "web" / name).read_text():
            raise ValueError("The explorer's artifact URL contract changed; update the exporter")
    output.mkdir(parents=True, exist_ok=False)
    for name, (prefix, source) in pages.items():
        destination = f"./artifacts/{quote(source.name, safe='')}/"
        (output / name).write_text((ROOT / "web" / name).read_text().replace(prefix, destination))
        shutil.copytree(source, output / "artifacts" / source.name)
    # The Part 2 page reads committed evidence; "../" points at the repository root in web/.
    for name in ("evaluators.html", "evaluators.js"):
        (output / name).write_text((ROOT / "web" / name).read_text().replace("../", "./"))
    for name in ("style.css", "app.js", "campaign.js"):
        shutil.copyfile(ROOT / "web" / name, output / name)
    shutil.copytree(ROOT / "reports/article-02", output / "reports/article-02")
    shutil.copytree(EXPERIMENT, output / "experiments/evaluator-exploits")


class LocalHandler(SimpleHTTPRequestHandler):
    """Serve only the public folders to loopback Host names, never the repository root."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_head(self):
        port = self.server.server_address[1]
        path = Path(self.translate_path(self.path)).relative_to(ROOT)
        if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"} or (
            path.parts[:1] not in {(name,) for name in PUBLIC_DIRS}
        ):
            self.send_error(404)
            return None
        return super().send_head()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "evaluate"):
        command = sub.add_parser(
            name, help="Run the baseline and candidates in fresh scenario state"
        )
        command.add_argument("--output", type=Path)
        if name == "evaluate":
            command.add_argument("--candidate", type=Path, required=True)
            command.add_argument(
                "--release",
                type=Path,
                required=True,
                help="Verified parent release whose lineage this candidate extends",
            )
    command = sub.add_parser("verify", help="Verify the release file inventory and SHA-256 hashes")
    command.add_argument("release", type=Path)
    command.add_argument(
        "--source",
        action="store_true",
        help="Also check that the recorded source files are unchanged",
    )
    command = sub.add_parser("serve", help="Serve the local browser pages on loopback")
    command.add_argument("--port", type=int, default=8075)
    command = sub.add_parser("site", help="Export a portable static explorer and verified evidence")
    command.add_argument("--release", type=Path, default=ROOT / "artifacts/article-01.6")
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--campaign-release", type=Path, default=ROOT / "artifacts/agent-study-03")
    command = sub.add_parser("campaign", help="Run the live outer LLM improvement agent")
    command.add_argument(
        "--live", action="store_true", required=True, help="Explicitly authorize API calls"
    )
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--campaigns", type=int, default=3)
    command.add_argument("--iterations", type=int, default=4)
    command.add_argument("--budget-usd", type=float, default=0.5)
    args = parser.parse_args()
    try:
        if args.command == "campaign":
            from .campaign import run_campaigns

            result = run_campaigns(args.output, args.campaigns, args.iterations, args.budget_usd)
            print(f"Recorded {len(result['campaigns'])} campaigns in {args.output}")
            print(f"Estimated model cost: ${result['estimated_cost_usd']:.6f}")
            if result["status"] != "completed":
                return 1
        elif args.command in {"run", "evaluate"}:
            output = args.output or ROOT / f"artifacts/local-{stamp()}"
            if output.exists():
                raise ValueError(f"Refusing to overwrite an existing release: {output}")
            extra = read_json(args.candidate) if args.command == "evaluate" else None
            if args.command == "evaluate" and not isinstance(extra, dict):
                raise ValueError("A submitted candidate must be a JSON object")
            parent_release = args.release if args.command == "evaluate" else None
            bundle, runs = build_bundle(extra, parent_release)
            bundle["release_id"] = output.name
            export(output, bundle, runs)
            verify(output)
            print(f"Wrote {len(runs)} scenario runs to {output}")
            for candidate in bundle["candidates"]:
                score = candidate["summary"]["metrics"]["task_success"]
                print(
                    f"{candidate['id']:20s} success={score:.1%} {candidate['recommendation']['status']}"
                )
            print("Every decision is pending human review. No candidate was promoted.")
        elif args.command == "verify":
            count = verify(args.release)
            if args.source:
                verify_source(args.release)
            print(
                f"Verified {count} artifact hashes" + (" and current source" if args.source else "")
            )
        elif args.command == "site":
            export_site(args.release, args.output, args.campaign_release)
            print(f"Portable static site: {args.output}; mount the directory at any URL prefix")
        elif args.command == "serve":
            if not 1024 <= args.port <= 65535:
                raise ValueError("Port must be between 1024 and 65535")
            server = ThreadingHTTPServer(("127.0.0.1", args.port), LocalHandler)
            base = f"http://127.0.0.1:{args.port}/web"
            print(f"Part 1: {base}/  ·  memory tool: {base}/memory.html", flush=True)
            print(f"Part 2: {base}/evaluators.html  ·  stop with Ctrl-C", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        return 0
    except (OSError, ValueError, KeyError, TypeError, TimeoutError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
