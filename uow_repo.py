import json
import uuid
from typing import Optional

from pydantic import BaseModel


class Entity(BaseModel):
    attr1: str
    id: Optional[str] = None


class AbstractRepo:
    def add(self, entity: Entity) -> str:
        pass

    def get(self, entity_id) -> Entity:
        pass


class SpecificRepo(AbstractRepo):
    def __init__(self, session: dict[str, Entity]):
        self.session = session

    def add(self, entity: Entity):
        new_id = str(uuid.uuid4())
        entity.id = new_id
        self.session[new_id] = entity
        return new_id

    def get(self, entity_id):
        return self.session[entity_id]


class FileUoW:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def __enter__(self):
        self.session: dict[str, Entity] = {}
        self._load()
        self.repo: AbstractRepo = SpecificRepo(self.session)
        return self

    def __exit__(self, *args):
        self.rollback()

    def _load(self):
        try:
            with open(self.file_path) as f:
                j = json.loads(f.read())
                self.session.clear()
                self.session.update({id_: Entity(**en) for id_, en in j.items()})
        except FileNotFoundError:
            pass

    def commit(self):
        s = {e.id: e.model_dump() for e in self.session.values()}
        with open(self.file_path, "w") as f:
            f.write(json.dumps(s))

    def rollback(self):
        self._load()


if __name__ == "__main__":
    with FileUoW("/tmp/db.json") as uow:
        uow.repo.add(Entity(attr1="xaxa"))
        uow.commit()
