"""Check the review item for an unchanged updater PR after successful reporting."""
import json
import os
import urllib.request
from pathlib import Path

ITEM = "- [ ] Ran `nixpkgs-review` on this PR. See [nixpkgs-review usage]."
SYSTEMS = ("x86_64-linux", "aarch64-linux", "x86_64-darwin", "aarch64-darwin", "riscv64-linux")


def checked_body(pr, reviewed, reports, inputs):
    """Return a narrowly edited body, or None when no edit is warranted."""
    if not reviewed["head"]["ref"].startswith("auto-update/"):
        return None
    if (pr["state"] != "open" or pr["number"] != reviewed["number"]
            or pr["head"]["sha"] != reviewed["head"]["sha"]
            or pr["head"]["repo"]["full_name"] != reviewed["head"]["repo"]["full_name"]):
        raise ValueError("PR identity or head changed since review; checklist not updated")
    if str(pr["number"]) != str(inputs["pr"]):
        raise ValueError("Review input does not match PR")
    expected = {s for s in SYSTEMS if (
        inputs.get(s) in ("yes_sandbox_false", "yes_sandbox_relaxed", "yes_sandbox_true")
        if s.endswith("darwin") else inputs.get(s) in (True, "true"))}
    if (not expected or not isinstance(reports, list) or len(reports) != len(expected)
            or {r.get("system") for r in reports} != expected):
        raise ValueError("Review reports do not cover exactly the requested systems")
    for report in reports:
        if report.get("head") != reviewed["head"]["sha"] or report.get("base") != reviewed["base"]["sha"]:
            raise ValueError("Review report commit mismatch")
        result = report.get("result", {})
        if not isinstance(result.get("failed"), list) or not isinstance(result.get("still_failing"), list):
            raise ValueError("Review report lacks build failure results")
        if result["failed"] or result["still_failing"]:
            return None
    body = pr.get("body") or ""
    lines = body.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == ITEM]
    checked = ITEM.replace("[ ]", "[x]", 1)
    if not matches and checked in body.splitlines():
        return None
    if len(matches) != 1:
        raise ValueError("Expected exactly one review checklist item; body left unchanged")
    index = matches[0]
    lines[index] = lines[index].replace("[ ]", "[x]", 1)
    return "".join(lines)


def main():
    reviewed = json.loads(os.environ["PR_JSON"])
    if not reviewed["head"]["ref"].startswith("auto-update/"):
        print("Not an updater PR; checklist left unchanged")
        return
    token = os.environ.get("PR_BODY_TOKEN", "")
    if not token:
        raise ValueError("Set GH_TOKEN or NIXPKGS_PR_TOKEN in the review runner with permission to edit the upstream PR")
    number = reviewed["number"]
    if type(number) is not int or number <= 0:
        raise ValueError("Invalid PR number")
    url = f"https://api.github.com/repos/NixOS/nixpkgs/pulls/{number}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "Content-Type": "application/json", "X-GitHub-Api-Version": "2026-03-10"}
    def request(method, data=None):
        req = urllib.request.Request(url, headers=headers, method=method,
                                     data=None if data is None else json.dumps(data).encode())
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response)
    pr = request("GET")
    body = checked_body(pr, reviewed, json.loads(Path("reports.json").read_text()),
                        json.loads(os.environ["INPUTS"]))
    if body is not None:
        request("PATCH", {"body": body})
        print(f"Checked nixpkgs-review item for PR #{number}")
    else:
        print("No checklist change needed")


if __name__ == "__main__":
    main()
