"""Verify publishing fails closed until exact explicit authorization."""
from datetime import UTC, datetime, timedelta
import pytest
from content_os.publishing.approval import (
    PublicationApproval, PublicationDenied, ReleaseManifest, assert_can_publish,
)

def fixtures():
    t = datetime(2026, 11, 23, tzinfo=UTC)
    m = ReleaseManifest(workflow_id="masld-21", revision_sha256="a"*64,
        asset_sha256="b"*64, caption_sha256="c"*64,
        destination_platform="youtube", destination_account_id="mha", status="approved")
    a = PublicationApproval(workflow_id=m.workflow_id,
        revision_sha256=m.revision_sha256, asset_sha256=m.asset_sha256,
        caption_sha256=m.caption_sha256, destination_platform=m.destination_platform,
        destination_account_id=m.destination_account_id, approved_by="owner",
        approved_at=t-timedelta(minutes=1), expires_at=t+timedelta(hours=1))
    return m,a,t

def check(m,a,t,**changes):
    assert_can_publish(m,a,now=t,authenticated_actor_id="owner",
        actor_is_authorized_publisher=True,production_enabled=True,**changes)

def test_exact_release_is_allowed():
    check(*fixtures())

def test_disabled_by_default():
    m,a,t=fixtures()
    with pytest.raises(PublicationDenied):
        assert_can_publish(m,a,now=t,authenticated_actor_id="owner",
            actor_is_authorized_publisher=True)

@pytest.mark.parametrize("field,value", [
    ("workflow_id","wrong"),("revision_sha256","d"*64),
    ("asset_sha256","e"*64),("caption_sha256","f"*64),
    ("destination_platform","instagram"),("destination_account_id","other")])
def test_changed_release_denied(field,value):
    m,a,t=fixtures()
    setattr(m,field,value)
    with pytest.raises(PublicationDenied):
        check(m,a,t)

def test_missing_approval_denied():
    m,a,t=fixtures()
    with pytest.raises(PublicationDenied):
        check(m,None,t)

def test_draft_denied():
    m,a,t=fixtures()
    m.status="draft"
    with pytest.raises(PublicationDenied):
        check(m,a,t)

def test_expired_denied():
    m,a,t=fixtures()
    a.expires_at=t
    with pytest.raises(PublicationDenied):
        check(m,a,t)

def test_identity_required():
    m,a,t=fixtures()
    with pytest.raises(PublicationDenied):
        assert_can_publish(m,a,now=t,authenticated_actor_id=None,
            actor_is_authorized_publisher=True,production_enabled=True)
    with pytest.raises(PublicationDenied):
        assert_can_publish(m,a,now=t,authenticated_actor_id="owner",
            actor_is_authorized_publisher=False,production_enabled=True)
