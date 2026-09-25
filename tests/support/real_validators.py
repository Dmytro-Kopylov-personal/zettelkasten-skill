"""Adapters for the *real* platform validators, skipped when they are not installed.

These are not reimplementations. `_validate_frontmatter` comes out of the Hermes agent's
own source, and `quick_validate.py` out of Anthropic's skill-creator; both run here
unmodified. What this buys is the same thing the YAML differential buys: the local
reimplementation in `src/render.py` and `tests/support/platform_rules.py` can be wrong
in the same direction as each other, and only an outside implementation can say so.

A validator that is absent is *skipped with a reason*, never stubbed. A stub would make
the suite green on a machine where the check cannot run, which is the failure mode this
whole repo is built to avoid.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERMES_ROOT = Path.home() / ".hermes" / "hermes-agent"
HERMES_TOOL = HERMES_ROOT / "tools" / "skill_manager_tool.py"
SKILL_CREATOR = Path.home() / ".hermes" / "skills" / "anthropic" / "skill-creator"
QUICK_VALIDATE = SKILL_CREATOR / "scripts" / "quick_validate.py"


def _load(module_name: str, path: Path, syspath: tuple[Path, ...] = ()) -> tuple[object | None, str]:
    if not path.is_file():
        return None, f"{path} is not installed on this machine"
    for entry in syspath:
        if str(entry) not in sys.path:
            sys.path.insert(0, str(entry))
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - any import failure is an environment fact
        return None, f"{path.name} is present but failed to import ({type(exc).__name__}: {exc})"
    return module, ""


def hermes_module() -> tuple[object | None, str]:
    return _load("hermes_skill_manager_tool", HERMES_TOOL, syspath=(HERMES_ROOT,))


def quick_validate_module() -> tuple[object | None, str]:
    return _load("anthropic_quick_validate", QUICK_VALIDATE, syspath=(SKILL_CREATOR / "scripts",))


def check_hermes(text: str) -> tuple[list[str], str]:
    """Run Hermes' own frontmatter and size validators over a rendered SKILL.md."""
    module, reason = hermes_module()
    if module is None:
        return [], reason
    problems = [p for p in (module._validate_frontmatter(text), module._validate_content_size(text)) if p]
    return problems, ""


def check_claude(skill_dir: Path) -> tuple[list[str], str]:
    """Run Anthropic's quick_validate over a directory containing SKILL.md."""
    module, reason = quick_validate_module()
    if module is None:
        return [], reason
    valid, message = module.validate_skill(skill_dir)
    return ([] if valid else [message]), ""
