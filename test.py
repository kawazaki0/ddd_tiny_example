#!/usr/bin/env -S uv run --script
#
# /// script
# dependencies = [
#    'pytest',
#    'pytest-asyncio',
#    'fastapi',
# ]
# ///
import pytest
from service_layer import (
    Todo,
    TodoService,
    InMemoryTodoRepository,
    TodoPolicy,
    InvalidTodoException,
    BusinessRuleViolation,
    ValidationError,
)


@pytest.mark.asyncio
async def test_create_todo():
    service = TodoService(InMemoryTodoRepository(), TodoPolicy())
    result = await service.create_todo("Buy milk")
    assert result.title == "Buy milk"


@pytest.mark.asyncio
async def test_create_todo_empty_title():
    service = TodoService(InMemoryTodoRepository(), TodoPolicy())
    with pytest.raises(ValidationError):
        await service.create_todo("")


@pytest.mark.asyncio
async def test_exceeds_limit():
    """Service should reject todo when limit reached"""
    service = TodoService(InMemoryTodoRepository(), TodoPolicy())
    for i in range(10):
        await service.create_todo(f"Todo {i}")

    with pytest.raises(BusinessRuleViolation):
        await service.create_todo("Todo 11")


def test_todo_invalid_title():
    """Todo entity should enforce business invariants"""
    with pytest.raises(InvalidTodoException):
        Todo(title="x" * 257)


if __name__ == "__main__":
    # Run with: uv run test.py
    pytest.main([__file__, "-v"])
