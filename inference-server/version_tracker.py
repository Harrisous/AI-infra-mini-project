from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VersionState:
    model_version: int
    model_repo_id: str


class VersionTracker:
    def __init__(self, initial_repo_id: str) -> None:
        self._state = VersionState(model_version=1, model_repo_id=initial_repo_id)

    def get(self) -> VersionState:
        return self._state

    def bump(self, new_repo_id: str) -> VersionState:
        self._state = VersionState(
            model_version=self._state.model_version + 1,
            model_repo_id=new_repo_id,
        )
        return self._state

