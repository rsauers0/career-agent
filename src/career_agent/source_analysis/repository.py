from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import TypeAdapter

from career_agent.source_analysis.models import (
    SourceAnalysisRun,
    SourceClarificationMessage,
    SourceClarificationQuestion,
)
from career_agent.storage import SNAPSHOTS_DIRNAME, timestamp_for_snapshot

SOURCE_ANALYSIS_DIRNAME = "source_analysis"
ANALYSIS_RUNS_FILENAME = "analysis_runs.json"
CLARIFICATION_QUESTIONS_FILENAME = "clarification_questions.json"
CLARIFICATION_MESSAGES_FILENAME = "clarification_messages.json"

_RUN_LIST_ADAPTER = TypeAdapter(list[SourceAnalysisRun])
_QUESTION_LIST_ADAPTER = TypeAdapter(list[SourceClarificationQuestion])
_MESSAGE_LIST_ADAPTER = TypeAdapter(list[SourceClarificationMessage])


class SourceAnalysisRepository:
    """File-backed storage boundary for source analysis workflow artifacts."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    @property
    def analysis_dir(self) -> Path:
        """Return the directory that stores source analysis data."""

        return self.data_dir / SOURCE_ANALYSIS_DIRNAME

    @property
    def runs_path(self) -> Path:
        """Return the JSON file path for source analysis runs."""

        return self.analysis_dir / ANALYSIS_RUNS_FILENAME

    @property
    def questions_path(self) -> Path:
        """Return the JSON file path for clarification questions."""

        return self.analysis_dir / CLARIFICATION_QUESTIONS_FILENAME

    @property
    def messages_path(self) -> Path:
        """Return the JSON file path for clarification messages."""

        return self.analysis_dir / CLARIFICATION_MESSAGES_FILENAME

    @property
    def snapshots_dir(self) -> Path:
        """Return the directory that stores source analysis snapshots."""

        return self.data_dir / SNAPSHOTS_DIRNAME / SOURCE_ANALYSIS_DIRNAME

    def list_runs(self, role_id: str | None = None) -> list[SourceAnalysisRun]:
        """Load all source analysis runs, optionally filtered by role id."""

        runs = self._load_runs()
        if role_id is None:
            return runs
        return [run for run in runs if run.role_id == role_id]

    def get_run(self, run_id: str) -> SourceAnalysisRun | None:
        """Load one source analysis run by identifier if it exists."""

        for run in self._load_runs():
            if run.id == run_id:
                return run
        return None

    def save_run(self, run: SourceAnalysisRun) -> None:
        """Create or update one source analysis run."""

        runs = [existing_run for existing_run in self._load_runs() if existing_run.id != run.id]
        runs.append(run)
        self._save_runs(runs)

    def list_questions(self, analysis_run_id: str) -> list[SourceClarificationQuestion]:
        """Load all clarification questions for one source analysis run."""

        return [
            question
            for question in self._load_questions()
            if question.analysis_run_id == analysis_run_id
        ]

    def get_question(self, question_id: str) -> SourceClarificationQuestion | None:
        """Load one clarification question by identifier if it exists."""

        for question in self._load_questions():
            if question.id == question_id:
                return question
        return None

    def save_question(self, question: SourceClarificationQuestion) -> None:
        """Create or update one clarification question."""

        questions = [
            existing_question
            for existing_question in self._load_questions()
            if existing_question.id != question.id
        ]
        questions.append(question)
        self._save_questions(questions)

    def list_messages(self, question_id: str) -> list[SourceClarificationMessage]:
        """Load all clarification messages for one question."""

        return [message for message in self._load_messages() if message.question_id == question_id]

    def get_message(self, message_id: str) -> SourceClarificationMessage | None:
        """Load one clarification message by identifier if it exists."""

        for message in self._load_messages():
            if message.id == message_id:
                return message
        return None

    def save_message(self, message: SourceClarificationMessage) -> None:
        """Create or update one clarification message."""

        messages = [
            existing_message
            for existing_message in self._load_messages()
            if existing_message.id != message.id
        ]
        messages.append(message)
        self._save_messages(messages)

    def _load_runs(self) -> list[SourceAnalysisRun]:
        """Load all source analysis runs from disk in stored order."""

        if not self.runs_path.exists():
            return []

        return _RUN_LIST_ADAPTER.validate_json(self.runs_path.read_text(encoding="utf-8"))

    def _load_questions(self) -> list[SourceClarificationQuestion]:
        """Load all clarification questions from disk in stored order."""

        if not self.questions_path.exists():
            return []

        return _QUESTION_LIST_ADAPTER.validate_json(self.questions_path.read_text(encoding="utf-8"))

    def _load_messages(self) -> list[SourceClarificationMessage]:
        """Load all clarification messages from disk in stored order."""

        if not self.messages_path.exists():
            return []

        return _MESSAGE_LIST_ADAPTER.validate_json(self.messages_path.read_text(encoding="utf-8"))

    def _save_runs(self, runs: list[SourceAnalysisRun]) -> None:
        """Persist the complete source analysis run list to disk."""

        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_file(self.runs_path, ANALYSIS_RUNS_FILENAME)
        self.runs_path.write_text(
            _RUN_LIST_ADAPTER.dump_json(runs, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _save_questions(self, questions: list[SourceClarificationQuestion]) -> None:
        """Persist the complete clarification question list to disk."""

        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_file(
            self.questions_path,
            CLARIFICATION_QUESTIONS_FILENAME,
        )
        self.questions_path.write_text(
            _QUESTION_LIST_ADAPTER.dump_json(questions, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _save_messages(self, messages: list[SourceClarificationMessage]) -> None:
        """Persist the complete clarification message list to disk."""

        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_existing_file(
            self.messages_path,
            CLARIFICATION_MESSAGES_FILENAME,
        )
        self.messages_path.write_text(
            _MESSAGE_LIST_ADAPTER.dump_json(messages, indent=2).decode("utf-8"),
            encoding="utf-8",
        )

    def _snapshot_existing_file(self, path: Path, filename: str) -> None:
        """Copy an existing source analysis table before overwriting it."""

        if not path.exists():
            return

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = self.snapshots_dir / f"{timestamp_for_snapshot()}-{filename}"
        shutil.copy2(path, snapshot_path)
