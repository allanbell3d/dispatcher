#!/usr/bin/env python3
"""Test Wave4 T0: pre-flight directory and file creation."""
import json, os, sys, tempfile
from pathlib import Path

def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{status}: {label}" + (f" -- {detail}" if detail else ""))
    return condition

if __name__ == "__main__":
    passed = True

    # Check sprint_profiles dir exists
    root = Path(__file__).resolve().parents[0]
    sp_dir = root / "sprint_profiles"
    passed &= check("sprint_profiles dir exists", sp_dir.is_dir(), str(sp_dir))

    # Check default.json exists and is valid JSON
    default_profile = sp_dir / "default.json"
    passed &= check("default.json exists", default_profile.is_file())
    if default_profile.is_file():
        try:
            data = json.loads(default_profile.read_text(encoding="utf-8"))
            passed &= check("default.json is valid JSON", isinstance(data, dict))
            passed &= check("default.json has hooks key", "hooks" in data)
        except Exception as e:
            passed &= check("default.json parse", False, str(e))

    sys.exit(0 if passed else 1)
