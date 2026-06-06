#!/usr/bin/env python3
"""Conformance verification for PyPepper's Lithos adoption manifest.

Pure standard-library checker (no third-party JSON Schema library) for the single
adoption manifest this repository publishes at
``docs/lithos/adoption-manifest.json``. It enforces the governance invariants the
Lithos standard documents in ``docs/conformance-and-fixtures.md`` and validates
against ``schemas/lithos-adoption-manifest.schema.json`` from
https://github.com/jovijovi/lithos.

A manifest declares conformance; it never authorizes anything. These checks
verify the declaration is internally consistent with the governance model and is
free of secret-shaped or private machine-local values.

Beyond the Lithos standalone checker, this adopting-project verifier also
performs the **file-presence** check the standalone checker explicitly defers to
the adopting project: the path named in ``local_workflow_file`` must actually
exist in this repository, so the manifest cannot point at a workflow file that
was never written.

To stay honest, the checker self-tests on startup: it mutates a known-good
manifest in memory and confirms each invalid case fails for its intended reason.
Sensitive probes are assembled at runtime from fragments, so no secret-shaped or
private literal is ever stored in this file.

Usage
-----
    python3 scripts/verify_lithos_conformance.py
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/lithos/adoption-manifest.json"

ADOPTION_PROFILES = {"lighter-governed-workflow", "full-governed-project"}

# The adoption-manifest format version this checker validates.
MANIFEST_FORMAT_VERSION = "1.0"

REQUIRED_TOP_LEVEL = [
    "manifest_version",
    "lithos_version",
    "adoption_profile",
    "conformance_claim",
    "local_workflow_file",
    "roles",
    "approval_gates",
    "approval_authority",
    "verification",
    "autonomous_pr_policy",
]

REQUIRED_ROLES = [
    "owner",
    "controller",
    "architect",
    "implementation_agent",
    "reviewer",
    "verifier",
]

REQUIRED_GATES = [
    "preparation",
    "implementation",
    "destructive_external",
    "live_runtime",
]

# Gates whose owner approval can never be waived.
OWNER_APPROVAL_GATES = ["implementation", "destructive_external"]

# Autonomous-PR actions Lithos adoption never licenses: each must be false.
FORBIDDEN_PR_ACTIONS = [
    "agent_self_approval",
    "agent_self_merge",
    "ownerless_auto_merge",
    "ownerless_branch_deletion",
    "ownerless_release_or_publish",
    "live_or_runtime_default_on",
]

# Actions that must remain behind explicit owner approval.
REQUIRED_PR_APPROVALS = [
    "merge",
    "branch-deletion",
    "release-or-publish",
    "live-runtime",
    "external-destructive",
]

REQUIRED_KNOWLEDGE_GOVERNANCE = [
    "dev_log",
    "lessons",
    "practices",
    "generated_index",
    "drift_report",
    "evidence_retention",
    "stale_knowledge_handling",
]

# Secret/token shapes. Each needle is assembled from fragments so this file never
# contains a value that matches one of its own patterns.
SECRET_PATTERNS = [
    re.compile("gh" + "p_[A-Za-z0-9]{20,}"),
    re.compile("github" + "_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?<![A-Za-z0-9])" + "sk-" + r"[A-Za-z0-9-]{20,}"),
    re.compile("AK" + "IA[A-Z0-9]{16}"),
    re.compile("xox" + r"[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile("-----BEGIN" + r"[A-Z ]*PRIVATE KEY-----"),
    re.compile(
        r"(?i)(api|access|secret|private|auth)[_-]?(key|token)\s*[:=]\s*"
        r"['\"]?[A-Za-z0-9_./+=-]{16,}"
    ),
]

PRIVATE_PATH_BOUNDARY = r"""(?=$|[/\s`'")\]},:;.])"""
_ROOT_HOME = "/" + "root"
PRIVATE_PATH_PATTERNS = [
    re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+" + PRIVATE_PATH_BOUNDARY),
    re.compile(_ROOT_HOME + PRIVATE_PATH_BOUNDARY),
    re.compile(r"(?i)[A-Za-z]:[\\/]Users[\\/][^\\/\s]+"),
]


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def is_nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _looks_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in SECRET_PATTERNS)


def _looks_private_path(value: str) -> bool:
    return any(pattern.search(value) for pattern in PRIVATE_PATH_PATTERNS)


def validate_manifest(data: object) -> list[str]:
    """Return a list of governance-invariant violations; empty means conforming."""
    reasons: list[str] = []

    if not isinstance(data, dict):
        return ["manifest must be a JSON object"]

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            reasons.append(f"missing required field: {key}")

    if data.get("manifest_version") != MANIFEST_FORMAT_VERSION:
        reasons.append(
            f"manifest_version must be the string {MANIFEST_FORMAT_VERSION!r} "
            "(the adoption-manifest format version this checker validates)"
        )
    if not is_nonempty_str(data.get("lithos_version")):
        reasons.append("lithos_version must be a non-empty string")
    reasons.extend(_validate_conformance_claim(data.get("conformance_claim")))

    profile = data.get("adoption_profile")
    if profile not in ADOPTION_PROFILES:
        reasons.append(
            "adoption_profile must be one of "
            f"{sorted(ADOPTION_PROFILES)} (got {profile!r})"
        )

    reasons.extend(_validate_workflow_path(data.get("local_workflow_file")))
    reasons.extend(_validate_roles(data.get("roles")))
    reasons.extend(_validate_gates(data.get("approval_gates")))
    reasons.extend(_validate_authority(data.get("approval_authority")))
    reasons.extend(_validate_verification(data.get("verification")))
    reasons.extend(_validate_pr_policy(data.get("autonomous_pr_policy")))

    if profile == "full-governed-project":
        reasons.extend(_validate_knowledge_governance(data.get("knowledge_governance")))

    _scan_sensitive_values(data, "", reasons)
    return reasons


def _validate_workflow_path(workflow: object) -> list[str]:
    """Enforce that ``local_workflow_file`` is one portable, repo-relative path."""
    if isinstance(workflow, list):
        return ["local_workflow_file must be a single string, not an array"]
    if not is_nonempty_str(workflow):
        return ["local_workflow_file must be a single non-empty string"]

    reasons: list[str] = []
    if workflow.startswith("~"):
        reasons.append(
            "local_workflow_file must be a portable repo-relative path, "
            "not a home directory reference"
        )
    if workflow.startswith("/") or re.match(r"[A-Za-z]:[\\/]", workflow):
        reasons.append(
            "local_workflow_file must be a repo-relative path, not an absolute path"
        )
    if "\\" in workflow:
        reasons.append("local_workflow_file must use portable '/' separators, not '\\'")
    if "://" in workflow:
        reasons.append("local_workflow_file must be a repo-relative path, not a URL")

    parts = workflow.split("/")
    if any(part == ".." for part in parts):
        reasons.append("local_workflow_file must not contain path traversal ('..')")
    if not workflow.startswith("/") and any(part == "" for part in parts):
        reasons.append("local_workflow_file must not contain an empty path segment")
    return reasons


def _scan_sensitive_values(node: object, path: str, reasons: list[str]) -> None:
    """Recursively flag any string value that is secret-shaped or a private path."""
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            _scan_sensitive_values(value, child, reasons)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _scan_sensitive_values(value, f"{path}[{index}]", reasons)
    elif isinstance(node, str):
        label = path or "manifest"
        if _looks_secret(node):
            reasons.append(f"{label} must not contain a secret-shaped value")
        elif _looks_private_path(node):
            reasons.append(
                f"{label} must not contain a private machine-local absolute path"
            )


def _validate_conformance_claim(claim: object) -> list[str]:
    if not isinstance(claim, dict):
        return ["conformance_claim must be an object"]
    reasons: list[str] = []
    if claim.get("claims_conformance") is not True:
        reasons.append("conformance_claim.claims_conformance must be true")
    if not is_nonempty_str(claim.get("statement")):
        reasons.append("conformance_claim.statement must be a non-empty string")
    return reasons


def _validate_roles(roles: object) -> list[str]:
    reasons: list[str] = []
    if not isinstance(roles, dict):
        return ["roles must be an object"]
    for role in REQUIRED_ROLES:
        entry = roles.get(role)
        if not isinstance(entry, dict):
            reasons.append(f"roles.{role} must be present and an object")
            continue
        if not is_nonempty_str(entry.get("assigned_to")):
            reasons.append(f"roles.{role}.assigned_to must be a non-empty string")
    owner = roles.get("owner")
    if isinstance(owner, dict) and owner.get("human") is not True:
        reasons.append("roles.owner.human must be true (the owner is a human)")
    return reasons


def _validate_gates(gates: object) -> list[str]:
    reasons: list[str] = []
    if not isinstance(gates, dict):
        return ["approval_gates must be an object"]
    for gate in REQUIRED_GATES:
        if gate not in gates:
            reasons.append(f"approval_gates.{gate} must be present")
        elif not isinstance(gates.get(gate), dict):
            reasons.append(f"approval_gates.{gate} must be an object")
    for gate in OWNER_APPROVAL_GATES:
        entry = gates.get(gate)
        if isinstance(entry, dict) and entry.get("owner_approval_required") is not True:
            reasons.append(f"approval_gates.{gate}.owner_approval_required must be true")
    live = gates.get("live_runtime")
    if isinstance(live, dict):
        if live.get("owner_approval_required") is not True:
            reasons.append(
                "approval_gates.live_runtime.owner_approval_required must be true"
            )
        if live.get("separate_controls_required") is not True:
            reasons.append(
                "approval_gates.live_runtime.separate_controls_required must be true"
            )
    return reasons


def _validate_authority(authority: object) -> list[str]:
    reasons: list[str] = []
    if not isinstance(authority, dict):
        return ["approval_authority must be an object"]
    if authority.get("holder") != "owner":
        reasons.append("approval_authority.holder must be 'owner'")
    if authority.get("delegable_to_agent") is not False:
        reasons.append("approval_authority.delegable_to_agent must be false")
    if authority.get("separate_from_verification_evidence") is not True:
        reasons.append(
            "approval_authority.separate_from_verification_evidence must be true"
        )
    if authority.get("separate_from_run_records") is not True:
        reasons.append("approval_authority.separate_from_run_records must be true")
    return reasons


def _validate_verification(verification: object) -> list[str]:
    if not isinstance(verification, dict):
        return ["verification must be an object"]
    if verification.get("evidence_required") is not True:
        return ["verification.evidence_required must be true"]
    return []


def _validate_pr_policy(policy: object) -> list[str]:
    reasons: list[str] = []
    if not isinstance(policy, dict):
        return ["autonomous_pr_policy must be an object"]
    for action in FORBIDDEN_PR_ACTIONS:
        if policy.get(action) is not False:
            reasons.append(
                f"autonomous_pr_policy.{action} must be false; "
                "Lithos adoption never licenses it"
            )
    approvals = policy.get("owner_approval_required_for")
    if not isinstance(approvals, list):
        reasons.append("autonomous_pr_policy.owner_approval_required_for must be an array")
    else:
        for action in REQUIRED_PR_APPROVALS:
            if action not in approvals:
                reasons.append(
                    "autonomous_pr_policy.owner_approval_required_for must include "
                    f"'{action}'"
                )
    return reasons


def _validate_knowledge_governance(knowledge: object) -> list[str]:
    reasons: list[str] = []
    if not isinstance(knowledge, dict):
        return [
            "knowledge_governance is required for full-governed-project and must be an object"
        ]
    for field in REQUIRED_KNOWLEDGE_GOVERNANCE:
        if not is_nonempty_str(knowledge.get(field)):
            reasons.append(f"knowledge_governance.{field} must be a non-empty string")
    return reasons


def _known_good_manifest() -> dict:
    """A clean lighter-governed-workflow manifest used only to self-test the engine."""
    return {
        "manifest_version": "1.0",
        "lithos_version": "1.x",
        "adoption_profile": "lighter-governed-workflow",
        "conformance_claim": {
            "claims_conformance": True,
            "statement": "conforms to Lithos 1.x at the lighter-governed-workflow depth",
        },
        "local_workflow_file": "docs/AI_FLOW.md",
        "roles": {
            "owner": {"assigned_to": "the project maintainer", "human": True},
            "controller": {"assigned_to": "the maintainer or an orchestrating agent"},
            "architect": {"assigned_to": "the maintainer"},
            "implementation_agent": {"assigned_to": "a contributor or an AI agent"},
            "reviewer": {"assigned_to": "a contributor independent of implementation"},
            "verifier": {"assigned_to": "the CI system and the reviewer"},
        },
        "approval_gates": {
            "preparation": {"owner_approval_required": False, "standing_authorization": True},
            "implementation": {"owner_approval_required": True, "granted_by": "owner"},
            "destructive_external": {
                "owner_approval_required": True,
                "granted_by": "owner",
                "per_action": True,
            },
            "live_runtime": {
                "in_scope": False,
                "owner_approval_required": True,
                "separate_controls_required": True,
            },
        },
        "approval_authority": {
            "holder": "owner",
            "delegable_to_agent": False,
            "separate_from_verification_evidence": True,
            "separate_from_run_records": True,
        },
        "verification": {"evidence_required": True, "independent_of_implementation": True},
        "autonomous_pr_policy": {
            "agent_may_open_pr": True,
            "agent_may_update_pr": True,
            "agent_self_approval": False,
            "agent_self_merge": False,
            "ownerless_auto_merge": False,
            "ownerless_branch_deletion": False,
            "ownerless_release_or_publish": False,
            "live_or_runtime_default_on": False,
            "owner_approval_required_for": [
                "merge",
                "branch-deletion",
                "release-or-publish",
                "live-runtime",
                "external-destructive",
            ],
        },
    }


def run_self_tests() -> list[str]:
    """Prove the invariants by mutating a known-good manifest in memory.

    Sensitive probes are assembled from fragments at runtime, so no secret-shaped
    or private literal is stored in this file.
    """
    failures: list[str] = []
    base = _known_good_manifest()
    baseline = validate_manifest(base)
    if baseline:
        return [f"self-test: known-good manifest unexpectedly failed: {baseline}"]

    secret_probe = "gh" + "p_" + "S" * 32
    hyphenated_secret_probe = "sk-" + "proj-" + "T" * 28
    home_probe = "/" + "home/" + "examplecontributor/" + "project/AI_FLOW.md"
    root_probe = "/" + "root/" + ".bash" + "rc"

    # (description, key path into the manifest, replacement value, required marker)
    cases = [
        ("secret in roles.owner.assigned_to",
         ["roles", "owner", "assigned_to"], secret_probe, "secret-shaped"),
        ("hyphenated secret in roles.owner.assigned_to",
         ["roles", "owner", "assigned_to"], hyphenated_secret_probe, "secret-shaped"),
        ("home path in local_workflow_file",
         ["local_workflow_file"], home_probe, "private machine-local"),
        ("root home path in roles.reviewer.assigned_to",
         ["roles", "reviewer", "assigned_to"], root_probe, "private machine-local"),
        ("absolute local_workflow_file",
         ["local_workflow_file"], "/etc/lithos/AI_FLOW.md", "absolute"),
        ("url-like local_workflow_file",
         ["local_workflow_file"], "https://example.invalid/AI_FLOW.md", "URL"),
        ("path traversal in local_workflow_file",
         ["local_workflow_file"], "../" + "../outside/AI_FLOW.md", "path traversal"),
        ("empty segment in local_workflow_file",
         ["local_workflow_file"], "docs//AI_FLOW.md", "empty path segment"),
        ("non-string manifest_version",
         ["manifest_version"], 1, "manifest_version"),
        ("claims_conformance false",
         ["conformance_claim", "claims_conformance"], False, "claims_conformance"),
        ("self-merge permitted",
         ["autonomous_pr_policy", "agent_self_merge"], True, "agent_self_merge"),
        ("self-approval permitted",
         ["autonomous_pr_policy", "agent_self_approval"], True, "agent_self_approval"),
        ("approval delegable to agent",
         ["approval_authority", "delegable_to_agent"], True, "delegable_to_agent"),
        ("implementation gate waived",
         ["approval_gates", "implementation", "owner_approval_required"], False,
         "approval_gates.implementation.owner_approval_required"),
        ("live_runtime controls waived",
         ["approval_gates", "live_runtime", "separate_controls_required"], False,
         "approval_gates.live_runtime.separate_controls_required"),
        ("unknown adoption_profile",
         ["adoption_profile"], "minimal", "adoption_profile"),
    ]
    for description, key_path, value, marker in cases:
        mutated = copy.deepcopy(base)
        target = mutated
        for key in key_path[:-1]:
            target = target[key]
        target[key_path[-1]] = value
        reasons = validate_manifest(mutated)
        if not any(marker in reason for reason in reasons):
            failures.append(
                f"self-test: mutation '{description}' did not fail for '{marker}'; "
                f"reasons were: {reasons}"
            )

    # A benign hyphenated token must not be misflagged as a secret.
    benign = copy.deepcopy(base)
    benign["roles"]["owner"]["assigned_to"] = "task-" + "1" * 30
    if any("secret-shaped" in reason for reason in validate_manifest(benign)):
        failures.append("self-test: a benign hyphenated token was misflagged as secret-shaped")
    return failures


def main() -> int:
    self_test_failures = run_self_tests()
    if self_test_failures:
        print("Conformance checker self-test failed:")
        for failure in self_test_failures:
            print(f"- {failure}")
        return 2

    if not MANIFEST_PATH.exists():
        print("Lithos conformance verification failed:")
        print(f"- missing adoption manifest: {MANIFEST_PATH.relative_to(ROOT)}")
        return 1

    try:
        data = load_json(MANIFEST_PATH)
    except json.JSONDecodeError as exc:
        print("Lithos conformance verification failed:")
        print(f"- {MANIFEST_PATH.relative_to(ROOT)}: invalid JSON: {exc}")
        return 1

    reasons = validate_manifest(data)

    # Adopting-project presence check: the referenced workflow file must exist.
    if isinstance(data, dict):
        workflow = data.get("local_workflow_file")
        if is_nonempty_str(workflow) and not _validate_workflow_path(workflow):
            if not (ROOT / workflow).is_file():
                reasons.append(
                    f"local_workflow_file points to '{workflow}', which does not "
                    "exist in this repository"
                )

    if reasons:
        print("Lithos conformance verification failed:")
        for reason in reasons:
            print(f"- {reason}")
        return 1

    print("Lithos conformance verification passed.")
    print(
        f"Self-tested the invariants and validated {MANIFEST_PATH.relative_to(ROOT)} "
        f"(profile: {data.get('adoption_profile')})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
