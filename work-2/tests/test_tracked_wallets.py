import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from polyalgo.db import init_db
from polyalgo.ingest.tracked_wallets import add_wallet, remove_wallet, list_wallets, mark_ingested


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}, future=True
    )
    init_db(engine)
    yield engine


def test_add_wallet_creates_new_entry(db_engine):
    result = add_wallet("0xABC", label="alice", source="manual", engine=db_engine)
    assert result["status"] == "added"
    assert result["wallet"] == "0xabc"

    wallets = list_wallets(engine=db_engine)
    assert len(wallets) == 1
    assert wallets[0]["wallet_address"] == "0xabc"
    assert wallets[0]["label"] == "alice"


def test_add_wallet_is_case_insensitive_upsert(db_engine):
    add_wallet("0xABC", label="alice", engine=db_engine)
    result = add_wallet("0xabc", label="alice updated", engine=db_engine)
    assert result["status"] == "updated"

    wallets = list_wallets(engine=db_engine)
    assert len(wallets) == 1
    assert wallets[0]["label"] == "alice updated"


def test_add_wallet_keeps_existing_label_when_none_given(db_engine):
    add_wallet("0xabc", label="alice", engine=db_engine)
    add_wallet("0xabc", label=None, engine=db_engine)

    wallets = list_wallets(engine=db_engine)
    assert wallets[0]["label"] == "alice"


def test_remove_wallet_soft_deletes(db_engine):
    add_wallet("0xabc", label="alice", engine=db_engine)
    result = remove_wallet("0xabc", engine=db_engine)
    assert result["status"] == "removed"

    active = list_wallets(active_only=True, engine=db_engine)
    assert active == []

    all_wallets = list_wallets(active_only=False, engine=db_engine)
    assert len(all_wallets) == 1
    assert all_wallets[0]["is_active"] == 0


def test_remove_wallet_not_found(db_engine):
    result = remove_wallet("0xdoesnotexist", engine=db_engine)
    assert result["status"] == "not_found"


def test_readding_a_removed_wallet_reactivates_it(db_engine):
    add_wallet("0xabc", label="alice", engine=db_engine)
    remove_wallet("0xabc", engine=db_engine)
    add_wallet("0xabc", label="alice again", engine=db_engine)

    active = list_wallets(active_only=True, engine=db_engine)
    assert len(active) == 1
    assert active[0]["label"] == "alice again"


def test_list_wallets_includes_score_columns_when_absent(db_engine):
    add_wallet("0xabc", label="alice", engine=db_engine)
    wallets = list_wallets(engine=db_engine)
    assert wallets[0]["final_score"] is None
    assert wallets[0]["classification"] is None


def test_mark_ingested_updates_timestamp(db_engine):
    add_wallet("0xabc", label="alice", engine=db_engine)
    before = list_wallets(engine=db_engine)[0]
    assert before["last_ingested_at"] is None

    mark_ingested("0xabc", engine=db_engine)
    after = list_wallets(engine=db_engine)[0]
    assert after["last_ingested_at"] is not None
