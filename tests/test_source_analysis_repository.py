from pydantic import TypeAdapter

from career_agent.source_analysis.models import (
    ClarificationMessageAuthor,
    SourceAnalysisRun,
    SourceAnalysisStatus,
    SourceClarificationMessage,
    SourceClarificationQuestion,
    SourceClarificationQuestionStatus,
    SourceFinding,
    SourceFindingStatus,
    SourceFindingType,
)
from career_agent.source_analysis.repository import (
    ANALYSIS_RUNS_FILENAME,
    CLARIFICATION_MESSAGES_FILENAME,
    CLARIFICATION_QUESTIONS_FILENAME,
    SOURCE_ANALYSIS_DIRNAME,
    SOURCE_FINDINGS_FILENAME,
    SourceAnalysisRepository,
)
from career_agent.storage import SNAPSHOTS_DIRNAME

RUN_LIST_ADAPTER = TypeAdapter(list[SourceAnalysisRun])
QUESTION_LIST_ADAPTER = TypeAdapter(list[SourceClarificationQuestion])
MESSAGE_LIST_ADAPTER = TypeAdapter(list[SourceClarificationMessage])
FINDING_LIST_ADAPTER = TypeAdapter(list[SourceFinding])


def build_run(
    *,
    run_id: str,
    role_id: str = "role-1",
    source_ids: list[str] | None = None,
    status: SourceAnalysisStatus = SourceAnalysisStatus.ACTIVE,
) -> SourceAnalysisRun:
    return SourceAnalysisRun(
        id=run_id,
        role_id=role_id,
        source_ids=source_ids or ["source-1"],
        status=status,
    )


def build_question(
    *,
    question_id: str,
    analysis_run_id: str = "run-1",
    question_text: str = "What measurable impact did this automation have?",
    relevant_source_ids: list[str] | None = None,
    status: SourceClarificationQuestionStatus = SourceClarificationQuestionStatus.OPEN,
) -> SourceClarificationQuestion:
    return SourceClarificationQuestion(
        id=question_id,
        analysis_run_id=analysis_run_id,
        question_text=question_text,
        relevant_source_ids=relevant_source_ids or [],
        status=status,
    )


def build_message(
    *,
    message_id: str,
    question_id: str = "question-1",
    author: ClarificationMessageAuthor = ClarificationMessageAuthor.USER,
    message_text: str = "It reduced weekly manual reconciliation.",
) -> SourceClarificationMessage:
    return SourceClarificationMessage(
        id=message_id,
        question_id=question_id,
        author=author,
        message_text=message_text,
    )


def build_finding(
    *,
    finding_id: str,
    analysis_run_id: str = "run-1",
    role_id: str = "role-1",
    source_id: str = "source-1",
    fact_id: str | None = "fact-1",
    finding_type: SourceFindingType = SourceFindingType.SUPPORTS_FACT,
    status: SourceFindingStatus = SourceFindingStatus.PROPOSED,
) -> SourceFinding:
    return SourceFinding(
        id=finding_id,
        analysis_run_id=analysis_run_id,
        role_id=role_id,
        source_id=source_id,
        fact_id=fact_id,
        finding_type=finding_type,
        proposed_fact_text=(
            "Led reporting automation for recurring team metrics."
            if finding_type == SourceFindingType.NEW_FACT
            else None
        ),
        rationale="The source describes the same automation work.",
        status=status,
    )


def test_source_analysis_repository_builds_storage_paths(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)

    assert repository.analysis_dir == tmp_path / SOURCE_ANALYSIS_DIRNAME
    assert repository.runs_path == (tmp_path / SOURCE_ANALYSIS_DIRNAME / ANALYSIS_RUNS_FILENAME)
    assert repository.questions_path == (
        tmp_path / SOURCE_ANALYSIS_DIRNAME / CLARIFICATION_QUESTIONS_FILENAME
    )
    assert repository.messages_path == (
        tmp_path / SOURCE_ANALYSIS_DIRNAME / CLARIFICATION_MESSAGES_FILENAME
    )
    assert repository.findings_path == (
        tmp_path / SOURCE_ANALYSIS_DIRNAME / SOURCE_FINDINGS_FILENAME
    )
    assert repository.snapshots_dir == (tmp_path / SNAPSHOTS_DIRNAME / SOURCE_ANALYSIS_DIRNAME)


def test_source_analysis_repository_lists_return_empty_when_missing(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)

    assert repository.list_runs() == []
    assert repository.list_questions("run-1") == []
    assert repository.list_messages("question-1") == []
    assert repository.list_findings() == []


def test_source_analysis_repository_saves_and_loads_runs(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    run = build_run(run_id="run-1")

    repository.save_run(run)

    assert repository.runs_path.exists()
    assert repository.list_runs() == [run]
    assert repository.get_run("run-1") == run


def test_source_analysis_repository_filters_runs_by_role_id(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    first_run = build_run(run_id="run-1", role_id="role-1")
    second_run = build_run(run_id="run-2", role_id="role-2")
    repository.save_run(first_run)
    repository.save_run(second_run)

    assert repository.list_runs(role_id="role-1") == [first_run]
    assert repository.list_runs(role_id="role-2") == [second_run]
    assert repository.list_runs(role_id="missing-role") == []


def test_source_analysis_repository_updates_existing_run_by_id(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    original_run = build_run(run_id="run-1")
    updated_run = build_run(
        run_id="run-1",
        source_ids=["source-1", "source-2"],
        status=SourceAnalysisStatus.COMPLETED,
    )
    repository.save_run(original_run)

    repository.save_run(updated_run)

    assert repository.list_runs() == [updated_run]


def test_source_analysis_repository_saves_and_loads_questions(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    question = build_question(question_id="question-1")

    repository.save_question(question)

    assert repository.questions_path.exists()
    assert repository.list_questions("run-1") == [question]
    assert repository.get_question("question-1") == question


def test_source_analysis_repository_filters_questions_by_analysis_run_id(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    first_question = build_question(question_id="question-1", analysis_run_id="run-1")
    second_question = build_question(question_id="question-2", analysis_run_id="run-2")
    repository.save_question(first_question)
    repository.save_question(second_question)

    assert repository.list_questions("run-1") == [first_question]
    assert repository.list_questions("run-2") == [second_question]
    assert repository.list_questions("missing-run") == []


def test_source_analysis_repository_updates_existing_question_by_id(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    original_question = build_question(question_id="question-1")
    updated_question = build_question(
        question_id="question-1",
        question_text="What measurable impact did this project have?",
        status=SourceClarificationQuestionStatus.RESOLVED,
    )
    repository.save_question(original_question)

    repository.save_question(updated_question)

    assert repository.list_questions("run-1") == [updated_question]


def test_source_analysis_repository_saves_and_loads_messages(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    message = build_message(message_id="message-1")

    repository.save_message(message)

    assert repository.messages_path.exists()
    assert repository.list_messages("question-1") == [message]
    assert repository.get_message("message-1") == message


def test_source_analysis_repository_filters_messages_by_question_id(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    first_message = build_message(message_id="message-1", question_id="question-1")
    second_message = build_message(message_id="message-2", question_id="question-2")
    repository.save_message(first_message)
    repository.save_message(second_message)

    assert repository.list_messages("question-1") == [first_message]
    assert repository.list_messages("question-2") == [second_message]
    assert repository.list_messages("missing-question") == []


def test_source_analysis_repository_updates_existing_message_by_id(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    original_message = build_message(message_id="message-1")
    updated_message = build_message(
        message_id="message-1",
        author=ClarificationMessageAuthor.ASSISTANT,
        message_text="Thanks, I captured that detail.",
    )
    repository.save_message(original_message)

    repository.save_message(updated_message)

    assert repository.list_messages("question-1") == [updated_message]


def test_source_analysis_repository_saves_and_loads_findings(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    finding = build_finding(finding_id="finding-1")

    repository.save_finding(finding)

    assert repository.findings_path.exists()
    assert repository.list_findings() == [finding]
    assert repository.get_finding("finding-1") == finding


def test_source_analysis_repository_filters_findings_by_relationship_ids(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    first_finding = build_finding(finding_id="finding-1")
    second_finding = build_finding(
        finding_id="finding-2",
        analysis_run_id="run-2",
        role_id="role-2",
        source_id="source-2",
        fact_id="fact-2",
    )
    repository.save_finding(first_finding)
    repository.save_finding(second_finding)

    assert repository.list_findings(analysis_run_id="run-1") == [first_finding]
    assert repository.list_findings(role_id="role-2") == [second_finding]
    assert repository.list_findings(source_id="source-1") == [first_finding]
    assert repository.list_findings(fact_id="fact-2") == [second_finding]
    assert repository.list_findings(role_id="missing-role") == []


def test_source_analysis_repository_updates_existing_finding_by_id(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    original_finding = build_finding(finding_id="finding-1")
    updated_finding = build_finding(
        finding_id="finding-1",
        status=SourceFindingStatus.ACCEPTED,
    )
    repository.save_finding(original_finding)

    repository.save_finding(updated_finding)

    assert repository.list_findings() == [updated_finding]


def test_source_analysis_repository_get_methods_return_none_when_missing(tmp_path) -> None:
    repository = SourceAnalysisRepository(tmp_path)

    assert repository.get_run("missing-run") is None
    assert repository.get_question("missing-question") is None
    assert repository.get_message("missing-message") is None
    assert repository.get_finding("missing-finding") is None


def test_source_analysis_repository_snapshots_existing_runs_file_before_overwrite(
    tmp_path,
) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    first_run = build_run(run_id="run-1")
    second_run = build_run(run_id="run-2")
    repository.save_run(first_run)

    repository.save_run(second_run)

    snapshots = list(repository.snapshots_dir.glob(f"*-{ANALYSIS_RUNS_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_runs = RUN_LIST_ADAPTER.validate_json(snapshots[0].read_text(encoding="utf-8"))
    assert snapshotted_runs == [first_run]
    assert repository.list_runs() == [first_run, second_run]


def test_source_analysis_repository_snapshots_existing_questions_file_before_overwrite(
    tmp_path,
) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    first_question = build_question(question_id="question-1")
    second_question = build_question(question_id="question-2")
    repository.save_question(first_question)

    repository.save_question(second_question)

    snapshots = list(repository.snapshots_dir.glob(f"*-{CLARIFICATION_QUESTIONS_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_questions = QUESTION_LIST_ADAPTER.validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_questions == [first_question]
    assert repository.list_questions("run-1") == [first_question, second_question]


def test_source_analysis_repository_snapshots_existing_messages_file_before_overwrite(
    tmp_path,
) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    first_message = build_message(message_id="message-1")
    second_message = build_message(message_id="message-2")
    repository.save_message(first_message)

    repository.save_message(second_message)

    snapshots = list(repository.snapshots_dir.glob(f"*-{CLARIFICATION_MESSAGES_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_messages = MESSAGE_LIST_ADAPTER.validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_messages == [first_message]
    assert repository.list_messages("question-1") == [first_message, second_message]


def test_source_analysis_repository_snapshots_existing_findings_file_before_overwrite(
    tmp_path,
) -> None:
    repository = SourceAnalysisRepository(tmp_path)
    first_finding = build_finding(finding_id="finding-1")
    second_finding = build_finding(finding_id="finding-2")
    repository.save_finding(first_finding)

    repository.save_finding(second_finding)

    snapshots = list(repository.snapshots_dir.glob(f"*-{SOURCE_FINDINGS_FILENAME}"))
    assert len(snapshots) == 1
    snapshotted_findings = FINDING_LIST_ADAPTER.validate_json(
        snapshots[0].read_text(encoding="utf-8")
    )
    assert snapshotted_findings == [first_finding]
    assert repository.list_findings() == [first_finding, second_finding]
