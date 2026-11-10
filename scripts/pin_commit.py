#!/usr/bin/env python3
"""
Keep METADATA.pb's `commit` on the revision the binaries were built from.

Google Fonts' tooling uses that field to fetch the upstream source matching
a submission. A pin that has drifted is worse than no pin: it points them at
a revision whose sources do not produce the fonts they are looking at.

Called by build.sh after gf_fixup.py. If the tree is dirty the pin is still
written, because HEAD is the closest honest answer, but it says so.
"""
import re, subprocess, sys


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()


def main(path):
    sha = git("rev-parse", "HEAD")
    if not sha:
        print("  not a git checkout; commit pin left alone")
        return
    dirty = bool(git("status", "--porcelain"))
    t = open(path).read()
    old = re.search(r'commit: "([a-f0-9]*)"', t)
    if not old:
        print("  no commit field in METADATA.pb")
        return
    if old.group(1) == sha:
        print(f"  commit pin already {sha[:7]}")
        return
    t = t.replace(old.group(0), f'commit: "{sha}"', 1)
    open(path, "w").write(t)
    note = "  (tree is dirty, so this revision does not contain every change)" if dirty else ""
    print(f"  commit pin {old.group(1)[:7] or 'none'} -> {sha[:7]}{note}")


if __name__ == "__main__":
    main(sys.argv[1])
