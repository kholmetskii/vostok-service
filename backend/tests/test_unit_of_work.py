import asyncio

import pytest

from app.infrastructure.db.uow import SQLAlchemyUnitOfWork


class FakeTransaction:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class FakeSession:
    def __init__(self):
        self.transaction = FakeTransaction()
        self.closed = False

    async def begin(self):
        return self.transaction

    async def close(self):
        self.closed = True


def test_unit_of_work_commits_and_closes_after_success():
    session = FakeSession()
    uow = SQLAlchemyUnitOfWork(lambda: session)

    async def operation():
        async with uow:
            pass

    asyncio.run(operation())

    assert session.transaction.committed is True
    assert session.transaction.rolled_back is False
    assert session.closed is True


def test_unit_of_work_rolls_back_and_closes_after_failure():
    session = FakeSession()
    uow = SQLAlchemyUnitOfWork(lambda: session)

    async def operation():
        with pytest.raises(RuntimeError, match="synthetic failure"):
            async with uow:
                raise RuntimeError("synthetic failure")

    asyncio.run(operation())

    assert session.transaction.committed is False
    assert session.transaction.rolled_back is True
    assert session.closed is True
