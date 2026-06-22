import pytest
from fastapi import HTTPException
from types import SimpleNamespace

from app.api.shared_inbox_endpoints import (
    AddMemberRequest,
    SharedInboxCreateRequest,
    add_shared_inbox_member,
    create_shared_inbox,
)
from app.models.billing_models import Subscription
from app.models.collaboration_models import SharedInbox, SharedInboxMember


class _FakeResult:
    def __init__(self, *, scalar_one_or_none_value=None, scalar_one_value=None):
        self._scalar_one_or_none_value = scalar_one_or_none_value
        self._scalar_one_value = scalar_one_value

    def scalar_one_or_none(self):
        return self._scalar_one_or_none_value

    def scalar_one(self):
        return self._scalar_one_value


class _FakeDB:
    def __init__(self, execute_results):
        self._execute_results = list(execute_results)
        self.added = []
        self.committed = False

    async def execute(self, _query):
        if not self._execute_results:
            raise AssertionError("Unexpected db.execute call with no queued fake result")
        return self._execute_results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        self.committed = True

    async def refresh(self, _obj):
        return None


@pytest.mark.asyncio
async def test_add_member_forbidden_for_member_role():
    inbox = SharedInbox(id="inbox-1", owner_user_id="owner-1", name="Support")
    current_member = SharedInboxMember(inbox_id="inbox-1", user_id="user-1", role="member")
    db = _FakeDB(
        [
            _FakeResult(scalar_one_or_none_value=inbox),
            _FakeResult(scalar_one_or_none_value=current_member),
        ]
    )
    current_user = SimpleNamespace(id="user-1", email="member@acme.com")

    with pytest.raises(HTTPException) as exc:
        await add_shared_inbox_member(
            inbox_id="inbox-1",
            request=AddMemberRequest(user_email="new-user@acme.com"),
            current_user=current_user,
            db=db,
        )

    assert exc.value.status_code == 403
    assert "cannot perform action 'add_member'" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_add_member_hits_team_seat_limit_for_admin():
    inbox = SharedInbox(id="inbox-2", owner_user_id="owner-2", name="Sales")
    admin_member = SharedInboxMember(inbox_id="inbox-2", user_id="admin-1", role="admin")
    owner_subscription = Subscription(
        user_id="owner-2",
        tenant_id="tenant-1",
        plan_id="team",
        plan_name="Team",
        price_usd=59,
        status="active",
        seats_included=2,
        seats_max=2,
        features={"shared_inboxes": True},
    )
    db = _FakeDB(
        [
            _FakeResult(scalar_one_or_none_value=inbox),
            _FakeResult(scalar_one_or_none_value=admin_member),
            _FakeResult(scalar_one_or_none_value=owner_subscription),
            _FakeResult(scalar_one_value=2),
        ]
    )
    current_user = SimpleNamespace(id="admin-1", email="admin@acme.com")

    with pytest.raises(HTTPException) as exc:
        await add_shared_inbox_member(
            inbox_id="inbox-2",
            request=AddMemberRequest(user_email="new-user@acme.com"),
            current_user=current_user,
            db=db,
        )

    assert exc.value.status_code == 403
    assert "Team seat limit reached" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_create_shared_inbox_hits_plan_limit():
    subscription = Subscription(
        user_id="owner-3",
        tenant_id="tenant-1",
        plan_id="team",
        plan_name="Team",
        price_usd=59,
        status="active",
        seats_included=5,
        seats_max=5,
        features={"shared_inboxes": True},
    )
    db = _FakeDB(
        [
            _FakeResult(scalar_one_or_none_value=subscription),
            _FakeResult(scalar_one_value=5),
        ]
    )
    current_user = SimpleNamespace(id="owner-3", email="owner@acme.com")

    with pytest.raises(HTTPException) as exc:
        await create_shared_inbox(
            request=SharedInboxCreateRequest(name="RevOps"),
            current_user=current_user,
            db=db,
        )

    assert exc.value.status_code == 403
    assert "Plan limit reached" in str(exc.value.detail)
