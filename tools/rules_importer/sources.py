# tools/rules_importer/sources.py
"""Machine-readable source allowlist and source-policy enforcement."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from .errors import SourcePolicyError
from .models import SourcePolicy


def validate_policy(policy: SourcePolicy) -> None:
    if not policy.allowed_for_ingestion:
        raise SourcePolicyError(f"source is not approved for ingestion: {policy.source_id}")
    if not policy.official:
        raise SourcePolicyError("official rules imports must use an official source")
    download = urlparse(policy.download_url)
    landing = urlparse(policy.landing_page_url)
    if download.scheme != "https" or landing.scheme != "https":
        raise SourcePolicyError("rules sources must use HTTPS")
    if download.hostname != "media.dndbeyond.com":
        raise SourcePolicyError("SRD download host is not approved")
    if landing.hostname != "www.dndbeyond.com" or landing.path != "/srd":
        raise SourcePolicyError("SRD landing page is not approved")
    if policy.license_id != "CC-BY-4.0":
        raise SourcePolicyError("SRD source must use the reviewed CC-BY-4.0 policy")
    if policy.media_type != "application/pdf":
        raise SourcePolicyError("v0.2 importer only accepts approved PDF sources")
    if policy.expected_sha256 is not None:
        if len(policy.expected_sha256) != 64:
            raise SourcePolicyError("expected SHA-256 must contain 64 hexadecimal characters")
        try:
            int(policy.expected_sha256, 16)
        except ValueError as exc:
            raise SourcePolicyError("expected SHA-256 must be hexadecimal") from exc


class SourceRegistry:
    def __init__(self, policies: tuple[SourcePolicy, ...]) -> None:
        ids = [policy.source_id for policy in policies]
        if len(ids) != len(set(ids)):
            raise SourcePolicyError("duplicate source_id in allowlist")
        self._policies = {policy.source_id: policy for policy in policies}

    @classmethod
    def from_path(cls, path: Path) -> SourceRegistry:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("sources"), list):
            raise SourcePolicyError("unsupported or malformed source allowlist")
        policies: list[SourcePolicy] = []
        for raw in data["sources"]:
            try:
                policies.append(SourcePolicy(**raw))
            except (TypeError, ValueError) as exc:
                raise SourcePolicyError("invalid source policy entry") from exc
        return cls(tuple(policies))

    def require(self, source_id: str) -> SourcePolicy:
        try:
            policy = self._policies[source_id]
        except KeyError as exc:
            raise SourcePolicyError(f"source is not allowlisted: {source_id}") from exc
        validate_policy(policy)
        return policy
