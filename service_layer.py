#!/usr/bin/env -S uv run --script
#
# /// script
# dependencies = [
#    'fastapi',
#    'uvicorn[standard]',
# ]
# ///
import abc
from abc import ABC
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException


# ============================================================================
# Domain layer
# ============================================================================

class DomainException(Exception):
    """Base for all domain errors"""
    pass


class InvalidTodoException(DomainException):
    pass

class TodoLimitReachedException(DomainException):
    pass


@dataclass
class Todo:
    """Domain entity - enforces business invariants"""

    title: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self):
        if not self.title or len(self.title.strip()) == 0:
            raise InvalidTodoException("Title cannot be empty")
        if len(self.title) > 256:
            raise InvalidTodoException("Title cannot exceed 256 characters")


class TodoPolicy:
    """Business rules - separate from service orchestration"""

    MAX_TODOS_PER_USER = 10

    @staticmethod
    def enforce_limit(current_todo_count: int) -> None:
        if current_todo_count >= TodoPolicy.MAX_TODOS_PER_USER:
            raise TodoLimitReachedException("Cannot create more todos, limit reached")


class TodoRepository(ABC):
    """Persistence abstraction - interface only"""

    @abc.abstractmethod
    async def save(self, todo: Todo) -> Todo:
        pass

    @abc.abstractmethod
    async def count_all(self) -> int:
        pass


# ============================================================================
# Infrastructure layer
# ============================================================================


class InMemoryTodoRepository(TodoRepository):
    """Concrete implementation - storage details hidden here"""

    def __init__(self):
        self._todos: dict[UUID, Todo] = {}

    async def save(self, todo: Todo) -> Todo:
        self._todos[todo.id] = todo
        return todo

    async def count_all(self) -> int:
        return len(self._todos)


# ============================================================================
# Application layer
# ============================================================================


@dataclass
class TodoDTO:
    """Data transfer object - service layer boundary"""

    id: UUID
    title: str


class ApplicationError(Exception):
    """Base for all application errors"""


class ValidationError(ApplicationError):
    pass


class BusinessRuleViolation(ApplicationError):
    pass


class TodoService:
    """Business orchestration - coordinates domain and infrastructure"""

    def __init__(self, repository: TodoRepository, todo_policy: TodoPolicy):
        self.repository = repository
        self.todo_policy = todo_policy

    async def create_todo(self, title: str) -> TodoDTO:
        count = await self.repository.count_all()
        try:
            self.todo_policy.enforce_limit(count)
        except TodoLimitReachedException as e:
            raise BusinessRuleViolation(str(e)) from e

        try:
            todo = Todo(title=title)
        except InvalidTodoException as e:
            raise ValidationError(str(e)) from e

        saved = await self.repository.save(todo)
        return TodoDTO(id=saved.id, title=saved.title)


# ============================================================================
# External layer
# ============================================================================

app = FastAPI(title="Todo API", version="0.1.0")


def create_service_container() -> TodoService:
    """Dependency injection - build service with all dependencies"""
    repository = InMemoryTodoRepository()
    policy = TodoPolicy()
    return TodoService(repository=repository, todo_policy=policy)


todo_service = create_service_container()


@app.post("/todos", status_code=201)
async def create_todo(request: dict):
    """HTTP endpoint - translates external requests to domain language"""
    try:
        todo = await todo_service.create_todo(request["title"])
        return {
            "id": todo.id,
            "title": todo.title,
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ex:app", host="127.0.0.1", port=8000, reload=True)
