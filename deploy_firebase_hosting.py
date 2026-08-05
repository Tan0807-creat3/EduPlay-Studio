import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


MODERN_SOURCE = Path("eduplay_studio") / "eduplay" / "resources" / "firebase_hosting"
LEGACY_SOURCE = Path("firebase_hosting")
STAGING_IGNORE_PATTERNS = (
    ".firebase",
    "__pycache__",
    "*firebase-adminsdk-*.json",
    "*service_account*.json",
    "*.fernet",
    "*.b64",
)


def resolve_repo_root(repo_root=None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    return Path(__file__).resolve().parent


def resolve_hosting_source(source: str = "modern", repo_root=None) -> Path:
    root = resolve_repo_root(repo_root)
    mode = str(source or "modern").strip().lower()
    if mode == "legacy":
        path = root / LEGACY_SOURCE
    else:
        path = root / MODERN_SOURCE
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy source hosting: {path}")
    return path


def stage_hosting_directory(source: str = "modern", repo_root=None, staging_root=None) -> Path:
    source_dir = resolve_hosting_source(source, repo_root=repo_root)
    stage_parent = Path(staging_root).resolve() if staging_root else Path(
        tempfile.mkdtemp(prefix=f"firebase-hosting-{source}-")
    )
    staged_dir = stage_parent / "hosting"
    if staged_dir.exists():
        shutil.rmtree(staged_dir)
    shutil.copytree(
        source_dir,
        staged_dir,
        ignore=shutil.ignore_patterns(*STAGING_IGNORE_PATTERNS),
    )
    return staged_dir


def firebase_cli_command():
    if os.name == "nt":
        return "firebase.cmd"
    return "firebase"


def deploy_hosting(source: str = "modern", repo_root=None, staging_root=None, keep_stage: bool = False) -> Path:
    staged_dir = stage_hosting_directory(source=source, repo_root=repo_root, staging_root=staging_root)
    try:
        subprocess.run(
            [firebase_cli_command(), "deploy", "--only", "hosting"],
            cwd=str(staged_dir),
            check=True,
        )
        return staged_dir
    finally:
        if not keep_stage:
            shutil.rmtree(staged_dir.parent, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy Firebase hosting từ source viewer mới hoặc thư mục legacy.")
    parser.add_argument("--source", choices=["modern", "legacy"], default="modern")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--keep-stage", action="store_true")
    args = parser.parse_args()
    source_dir = resolve_hosting_source(args.source, repo_root=args.repo_root or None)
    deploy_hosting(
        source=args.source,
        repo_root=args.repo_root or None,
        keep_stage=args.keep_stage,
    )
    print(f"Deployed hosting source '{args.source}' from {source_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
