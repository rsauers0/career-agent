from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import TypeAdapter

from career_agent.fact_review.models import (
    FactReviewAction,
    FactReviewMessage,
    FactReviewThread,
)
from career_agent.storage import SNAPSHOTS_DIRNAME, timestamp_for_snapshot

FACT_REVIEW_DIRNAME = "fact_review"
FACT_REVIEW_THREADS_FILENAME = "fact_review_threads.json"
FACT_REVIEW_MESSAGES_FILENAME = "fact_review_messages.json"
FACT_REVIEW_ACTIONS_FILENAME = "fact_review_actions.json"

_THREAD_LIST_ADAPTER = TypeAdapter(list[FactReviewThread])
_MESSAGE_LIST_ADAPTER = TypeAdapter(list[FactReviewMessage])
_ACTION_LIST_ADAPTER = TypeAdapter(list[FactReviewAction])


class FactReviewRepository:
    """File-backed storage boundary for fact review workflow artifacts."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    @property
    def review_dir(self) -> Path:
        """Return the directory that stores fact review data."""

        return self.data_dir / FACT_REVIEW_DIRNAME

    @property
    def threads_path(self) -> Path:
        """Return the JSON file path for fact review threads."""

        return self.review_dir / FACT_REVIEW_THREADS_FILENAME

    @property
    def messages_path(self) -> Path:
        """Return the JSON file path for fact review messages."""

        return self.review_dir / FACT_REVIEW_MESSAGES_FILENAME

    @property
    def actions_path(self) -> Path:
        """Return the JSON file path for fact review actions."""

        return self.review_dir / FACT_REVIEW_ACTIONS_FILENAME

    @property
    def snapshots_dir(self) -> Path:
        """Return the directory that stores fact review snapshots."""

        return self.data_dir / SNAPSHOTS_DIRNAME / FACT_REVIEW_DIRNAME

    def list_threads(
        self,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> list[FactReviewThread]:
        """Load fact review threads, optionally filtered by fact or role."""

        threads = self._load_threads()
        if fact_id is not None:
            threads = [thread for thread in threads if thread.fact_id == fact_id]
        if role_id is not None:
            threads = [thread for thread in threads if thread.role_id == role_id]
        return threads

    def get_thread(self, thread_id: str) -> FactReviewThread | None:
        """Load one fact review thread by identifier if it exists."""

        for thread in self._load_threads():
            if thread.id == thread_id:
                return thread
        return None

    def save_thread(self, thread: FactReviewThread) -> None:
        """Create or update one fact review thread."""

        threads = [
            existing_thread
            for existing_thread in self._load_threads()
            if existing_thread.id != thread.id
        ]
        threads.append(thread)
        self._save_threads(threads)

    def list_messages(self, thread_id: str) -> list[FactReviewMessage]:
        """Load all messages for one fact review thread."""

        return [message for message in self._load_messages() if message.thread_id == thread_id]

    def get_message(self, message_id: str) -> FactReviewMessage | None:
        """Load one fact review message by identifier if it exists."""

        for message in self._load_messages():
            if message.id == message_id:
                return message
        return None

    def save_message(self, message: FactReviewMessage) -> None:
        """Create or update one fact review message."""

        messages = [
            existing_message
            for existing_message in self._load_messages()
            if existing_message.id != message.id
        ]
        messages.append(message)
        self._save_messages(messages)

    def list_actions(
        self,
        thread_id: str | None = None,
        fact_id: str | None = None,
        role_id: str | None = None,
    ) -> list[FactReviewAction]:
        """Load fact review actions, optionally filtered by thread, fact, or role."""

        actions = self._load_actions()
        if thread_id is not None:
            actions = [action for action in actions if action.thread_id == thread_id]
        if fact_id is not None:
            actions = [action for action in actions if action.fact_id == fact_id]
        if role_id is not None:
            actions = [action for action in actions if action.role_id == role_id]
        return actions

    def get_action(self, action_id: str) -> FactReviewAction | None:
        """Load one fact review action by identifier if it exists."""

        for action in self._load_actions():
            if action.id == action_id:
                return action
        return None

    def save_action(self, action: FactReviewAction) -> None:
        """Create or update one fact review action."""

        actions = [
            existing_action
            for existing_action in self._load_actions()
            if existing_action.id != action.id
        ]
        actions.append(action)
        self._save_actions(actions)

    def _load_threads(self) -> list[FactReviewThread]:
        """Load all fact review threads from disk in stored order."""

        if not self.threads_path.exists():
            return []
        return _THREAD_LIST_ADAPTER.validate_json(self.threads_path.read_text(encoding="utf-8"))

    def _load_messages(self) -> list[FactReviewMessage]:
        """Load all fact review messages from disk in stored order."""

        if not self.messages_path.exists():
            return []
        return _MESSAGE_LIST_ADAPTER.validate_json(self.messages_path.read_text(encoding="utf-8"))

    def _load_actions(self) -> list[FactReviewAction]:
        """Load all fact review actions from disk in stored order."""

        if not self.actions_path.exists():
            return []
        return _ACTION_LIST_ADAPTER.validate_json(self.actions_path.read_text(encoding="utf-8"))

    def _save_threads(self, threads: list[FactReviewThread]) -> None:
        """Persist the complete fact review thread list."""

        self.review_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_file(self.threads_path, FACT_REVIEW_THREADS_FILENAME)
        self.threads_path.write_text(
            _THREAD_LIST_ADAPTER.dump_json(threads, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _save_messages(self, messages: list[FactReviewMessage]) -> None:
        """Persist the complete fact review message list."""

        self.review_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_file(self.messages_path, FACT_REVIEW_MESSAGES_FILENAME)
        self.messages_path.write_text(
            _MESSAGE_LIST_ADAPTER.dump_json(messages, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _save_actions(self, actions: list[FactReviewAction]) -> None:
        """Persist the complete fact review action list."""

        self.review_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_file(self.actions_path, FACT_REVIEW_ACTIONS_FILENAME)
        self.actions_path.write_text(
            _ACTION_LIST_ADAPTER.dump_json(actions, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _snapshot_existing_file(self, path: Path, filename: str) -> None:
        """Copy an existing fact review table before overwriting it."""

        if not path.exists():
            return

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self.snapshots_dir / f"{timestamp_for_snapshot()}-{filename}"
        shutil.copy2(path, snapshot_path)
