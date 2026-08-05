#!/usr/bin/env python3
"""`card-legal-data` 를 3개 휠로 분할 빌드한다.

## 왜 (2026-08-06)

첨부 PDF/HWP 본문을 회수하면서(파이프라인 #12~#15) 데이터가 커져 단일 휠이 **PyPI
기본 상한 100MB 를 넘었다** — 51MB → 100.3MB(실측 105,185,915 bytes)로 발행이 실패했다.

상한 증액(프로젝트별 요청)만으로는 다음 증가에서 또 막힌다. 데이터를 **용도별로 쪼개** 각
휠이 상한에 여유를 갖게 한다. 실측 구성(압축 전 416.4MB → 휠 100.3MB, 압축비 ≈ 4.15):

| 묶음 | 압축 전 | 휠(추정) | 내용 |
|---|---|---|---|
| core       | 247.7MB | ≈ 60MB | 법령·해석례·비조치·약관·가이드라인·안내서 — **자문 근거 본체** |
| press      | 102.0MB | ≈ 25MB | 보도자료 4종(fsc·fss·pipc·kisa) — 규범이 아니라 소식 |
| precedents |  66.7MB | ≈ 16MB | 상위 tier 판례(bulk 17만은 여전히 archive 별도 반입) |

## 설치 후 레이아웃은 단일 휠과 동일하다

세 휠 모두 `card_legal_data/` **같은 트리**에 파일을 넣는다. `__init__.py` 가 없는
네임스페이스 패키지이고 파일 경로가 겹치지 않으므로 pip 가 그대로 병합한다 →
`card_legal_data.__path__[0]` 이 병합된 디렉토리 하나를 가리킨다.
**따라서 LawAgent `ingest_from_legal_data.sh` 는 고칠 필요가 없다.**

내부망에서는 세 개를 함께 설치한다(부분 설치도 동작한다 — 적재 스크립트가 없는 폴더는
건너뛴다):

    pip install card-legal-data card-legal-data-press card-legal-data-precedents

## 구현 메모

빌드 디렉토리는 **하드링크**(`os.link`)로 만든다 — 400MB 를 복사하면 러너에서 느리고
디스크를 두 배로 쓴다. hatchling 은 `force-include` 로 데이터만 담고 `packages = []`
이므로 산출물에 .py 가 섞이지 않는다(발행 워크플로가 그것도 검사한다).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "legal_data"
BUILD = ROOT / "build"
DIST = ROOT / "dist"

# 휠 상한 — PyPI 기본값. 여유를 보기 위해 경고 문턱을 따로 둔다.
PYPI_LIMIT = 100 * 1024 * 1024
WARN_AT = 80 * 1024 * 1024

# 보도자료는 원천마다 폴더 이름이 같다 — 이 이름을 가진 하위 폴더 전부가 press 묶음이다.
PRESS_SUBDIR = "press_releases"
PRECEDENT_TOP = "precedents"

PACKAGES: dict[str, dict] = {
    "core": {
        "name": "card-legal-data",
        "description": "Versioned legal data for offline installation (core)",
    },
    "press": {
        "name": "card-legal-data-press",
        "description": "Versioned legal data — press releases",
    },
    "precedents": {
        "name": "card-legal-data-precedents",
        "description": "Versioned legal data — precedents (tier 1)",
    },
}

PYPROJECT = """\
[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[project]
name = "{name}"
dynamic = ["version"]
description = "{description}"
readme = "README.md"
requires-python = ">=3.9"
license = {{ text = "Proprietary" }}
classifiers = [
  "Programming Language :: Python :: 3",
  "Operating System :: OS Independent",
  "License :: Other/Proprietary License",
]

[tool.hatch.version]
source = "env"
variable = "HATCH_BUILD_VERSION"

[tool.hatch.build.targets.wheel]
packages = []

[tool.hatch.build.targets.wheel.force-include]
"legal_data" = "card_legal_data"
"""


def classify(rel: Path) -> str:
    """`legal_data` 기준 상대경로 → 어느 묶음인가."""
    parts = rel.parts
    if parts and parts[0] == PRECEDENT_TOP:
        return "precedents"
    if PRESS_SUBDIR in parts:
        return "press"
    return "core"


def stage(bucket: str) -> tuple[Path, int, int]:
    """빌드 디렉토리를 하드링크로 구성 → (경로, 파일 수, 바이트)."""
    root = BUILD / bucket
    if root.exists():
        shutil.rmtree(root)
    (root / "legal_data").mkdir(parents=True)
    shutil.copy2(ROOT / "README.md", root / "README.md")

    files = 0
    total = 0
    for src in DATA.rglob("*"):
        if not src.is_file() or src.name == ".DS_Store":
            continue
        rel = src.relative_to(DATA)
        if classify(rel) != bucket:
            continue
        dst = root / "legal_data" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(src, dst)          # 하드링크 — 복사 없이 같은 inode
        except OSError:
            shutil.copy2(src, dst)     # 크로스 디바이스 등은 복사로 폴백
        files += 1
        total += src.stat().st_size
    return root, files, total


def build(bucket: str, version: str) -> Path:
    meta = PACKAGES[bucket]
    root, files, total = stage(bucket)
    if files == 0:
        raise SystemExit(f"[{bucket}] 담을 파일이 0건이다 — 분류 규칙을 확인하라")
    (root / "pyproject.toml").write_text(
        PYPROJECT.format(name=meta["name"], description=meta["description"]),
        encoding="utf-8")

    env = {**os.environ, "HATCH_BUILD_VERSION": version}
    subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(DIST),
                    str(root)], check=True, env=env)
    wheel = max(DIST.glob(f"{meta['name'].replace('-', '_')}-*.whl"),
                key=lambda p: p.stat().st_mtime)
    size = wheel.stat().st_size
    print(f"  [{bucket}] {wheel.name}  {files:,}파일  "
          f"압축 전 {total / 1048576:.1f}MB → 휠 {size / 1048576:.1f}MB")
    if size >= PYPI_LIMIT:
        raise SystemExit(
            f"[{bucket}] 휠이 PyPI 상한을 넘었다: {size:,} bytes. "
            f"분할선을 다시 그어야 한다(scripts/build_wheels.py 상단 표 참조)")
    if size >= WARN_AT:
        print(f"  ⚠️  [{bucket}] 상한의 80%를 넘었다({size / 1048576:.1f}MB) — "
              f"다음 증가에 대비해 분할을 재검토할 것")
    return wheel


def main() -> None:
    ap = argparse.ArgumentParser(description="card-legal-data 분할 휠 빌드")
    ap.add_argument("--version", default=os.environ.get("HATCH_BUILD_VERSION"),
                    help="휠 버전(미지정 시 HATCH_BUILD_VERSION)")
    ap.add_argument("--only", choices=sorted(PACKAGES), action="append",
                    help="이 묶음만 빌드(반복 지정 가능)")
    ap.add_argument("--dry-run", action="store_true", help="분류 집계만 출력")
    args = ap.parse_args()

    if args.dry_run:
        agg: dict[str, list[int]] = {k: [0, 0] for k in PACKAGES}
        for src in DATA.rglob("*"):
            if not src.is_file() or src.name == ".DS_Store":
                continue
            b = classify(src.relative_to(DATA))
            agg[b][0] += 1
            agg[b][1] += src.stat().st_size
        for b, (n, sz) in agg.items():
            print(f"  {b:11s} {n:7,}파일  {sz / 1048576:8.1f}MB  "
                  f"→ 휠 추정 {sz / 1048576 / 4.15:6.1f}MB")
        return

    if not args.version:
        raise SystemExit("버전이 필요하다 — --version 또는 HATCH_BUILD_VERSION")
    DIST.mkdir(exist_ok=True)
    print(f"분할 휠 빌드 (version={args.version})")
    for bucket in (args.only or sorted(PACKAGES)):
        build(bucket, args.version)


if __name__ == "__main__":
    main()
