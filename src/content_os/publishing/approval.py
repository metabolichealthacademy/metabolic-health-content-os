"""Fail-closed authorization check for future social publishing adapters.

This module does not publish or issue approvals. Publisher identity must come
from server-side authentication, never an untrusted HTTP request field.
"""
from datetime import UTC, datetime
from typing import Literal
from pydantic import BaseModel, Field


class PublicationDenied(ValueError):
    """A release must not be posted."""


class ReleaseManifest(BaseModel):
    workflow_id: str = Field(min_length=1)
    revision_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    asset_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    caption_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    destination_platform: Literal["youtube", "instagram", "facebook", "tiktok", "x"]
    destination_account_id: str = Field(min_length=1)
    status: Literal["draft", "awaiting_approval", "approved", "published"] = "draft"


class PublicationApproval(BaseModel):
    workflow_id: str
    revision_sha256: str
    asset_sha256: str
    caption_sha256: str
    destination_platform: str
    destination_account_id: str
    approved_by: str = Field(min_length=1)
    approved_at: datetime
    expires_at: datetime


def assert_can_publish(
    manifest: ReleaseManifest,
    approval: PublicationApproval | None,
    *,
    authenticated_actor_id: str | None,
    actor_is_authorized_publisher: bool,
    production_enabled: bool = False,
    now: datetime | None = None,
) -> None:
    """Permit only the exact release an authenticated publisher approved.

    Call immediately before the external write. A future adapter must also
    record audit receipts and handle ambiguous remote outcomes without retry.
    """
    if not production_enabled:
        raise PublicationDenied("Publishing disabled")
    if manifest.status != "approved":
        raise PublicationDenied("Release not approved")
    if not authenticated_actor_id or not actor_is_authorized_publisher:
        raise PublicationDenied("Authenticated publisher required")
    if approval is None or approval.approved_by != authenticated_actor_id:
        raise PublicationDenied("Missing authenticated publisher approval")
    same_release = all(
        getattr(manifest, key) == getattr(approval, key)
        for key in ("workflow_id", "destination_platform", "destination_account_id")
    ) and all(
        getattr(manifest, key).lower() == getattr(approval, key).lower()
        for key in ("revision_sha256", "asset_sha256", "caption_sha256")
    )
    if not same_release:
        raise PublicationDenied("Release differs from approved version")
    checked_at = now or datetime.now(UTC)
    if approval.approved_at.tzinfo is None or approval.expires_at.tzinfo is None:
        raise PublicationDenied("Timezone-aware timestamps required")
    if not approval.approved_at <= checked_at < approval.expires_at:
        raise PublicationDenied("Approval not currently valid")
