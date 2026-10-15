# Diagnose Darwin sandbox disagreements with conditional `relaxed` reviews

## Summary

Run Darwin reviews with `sandbox = false` and `sandbox = true` first, then run `sandbox = relaxed` only when one mode fails.

## Motivation

The workflow currently selects only one sandbox mode for each Darwin system. A successful or failed result does not show whether the outcome depends on sandbox behavior.

If both `sandbox = false` and `sandbox = true` pass, there is no sandbox-dependent failure to diagnose. If both fail, the review is revealing a non-sandbox problem. In either case, `relaxed` adds no relevant information.

When only one passes, `relaxed` provides further clarification. As defined by the [Nix configuration reference](https://nix.dev/manual/nix/stable/command-ref/conf-file.html#conf-sandbox), it keeps ordinary derivations sandboxed while allowing fixed-output derivations and derivations with `__noChroot = true` to run unsandboxed. Its result can help locate the problem.

The proposed trigger is:

| `false` | `true` | Run `relaxed`? |
| --- | --- | --- |
| Pass | Pass | No |
| Pass | Fail | Yes |
| Fail | Pass | Yes |
| Fail | Fail | No |

Nixpkgs PR [#554418](https://github.com/NixOS/nixpkgs/pull/554418) is a recent example of where this could have been helpful.

## Proposed workflow

For each enabled Darwin system:

1. Run two primary reviews in parallel:
   - `sandbox = false`
   - `sandbox = true`
2. Upload a uniquely named report and execution-status artifact for each run.
3. for sandbox mod result comparison step:
   - require both primary reports;
   - verify that they describe the same PR head, base, merge commit, system, and review inputs;
   - derive each mode's pass/fail status from its normalized package report;
   - it should read `failed` and `still_failing` from each report. A mode fails if either list contains a package
   - If a report is missing or refers to a different PR commit, mark the comparison as incomplete instead of treating it as a pass.
   - emit the Darwin systems that require a `relaxed` run.
4. Run `sandbox = relaxed` for each selected system
5. Generate the final report after the optional `relaxed` stage has completed or been skipped
6. The final report lists every mode that ran

```text
prepare
   |
   +--> Darwin false --+
   |                   +--> compare --> relaxed when needed --+
   +--> Darwin true ---+                                  |
   |                                                       +--> final report/comment
   +--> other systems -------------------------------------+
```

the compare and conditional relaxed steps should be defined in the workflow file.

## Workflow changes

add the sandbox mode to report name for example `report_aarch64-darwin_sandbox_false.json`.
