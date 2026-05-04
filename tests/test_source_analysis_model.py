import pytest
from pydantic import ValidationError

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


def test_source_analysis_run_json_round_trip() -> None:
    run = SourceAnalysisRun(
        role_id="role-1",
        source_ids=["source-1", "source-2"],
        status=SourceAnalysisStatus.COMPLETED,
    )

    restored = SourceAnalysisRun.model_validate_json(run.model_dump_json())

    assert restored == run
    assert restored.id


def test_source_analysis_run_defaults_to_active() -> None:
    run = SourceAnalysisRun(
        role_id="role-1",
        source_ids=["source-1"],
    )

    assert run.status == SourceAnalysisStatus.ACTIVE
    assert run.created_at.tzinfo is not None
    assert run.updated_at.tzinfo is not None


def test_source_analysis_run_normalizes_role_and_source_ids() -> None:
    run = SourceAnalysisRun(
        role_id="  role-1  ",
        source_ids=["  source-1  ", "", "  source-2  "],
    )

    assert run.role_id == "role-1"
    assert run.source_ids == ["source-1", "source-2"]


def test_source_analysis_run_requires_role_id_and_source_ids() -> None:
    with pytest.raises(ValidationError):
        SourceAnalysisRun(
            role_id="",
            source_ids=["source-1"],
        )

    with pytest.raises(ValidationError):
        SourceAnalysisRun(
            role_id="role-1",
            source_ids=[],
        )


def test_source_analysis_run_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        SourceAnalysisRun(
            role_id="role-1",
            source_ids=["source-1"],
            created_at="2026-01-01T00:00:00",
        )


def test_source_clarification_question_json_round_trip() -> None:
    question = SourceClarificationQuestion(
        analysis_run_id="run-1",
        question_text="What measurable impact did this automation have?",
        relevant_source_ids=["source-1"],
        status=SourceClarificationQuestionStatus.RESOLVED,
    )

    restored = SourceClarificationQuestion.model_validate_json(question.model_dump_json())

    assert restored == question
    assert restored.id


def test_source_clarification_question_defaults_to_open() -> None:
    question = SourceClarificationQuestion(
        analysis_run_id="run-1",
        question_text="What measurable impact did this automation have?",
    )

    assert question.status == SourceClarificationQuestionStatus.OPEN
    assert question.relevant_source_ids == []
    assert question.created_at.tzinfo is not None
    assert question.updated_at.tzinfo is not None


def test_source_clarification_question_normalizes_text_fields() -> None:
    question = SourceClarificationQuestion(
        analysis_run_id="  run-1  ",
        question_text="  What measurable impact did this automation have?  ",
        relevant_source_ids=["  source-1  ", "", "  source-2  "],
    )

    assert question.analysis_run_id == "run-1"
    assert question.question_text == "What measurable impact did this automation have?"
    assert question.relevant_source_ids == ["source-1", "source-2"]


def test_source_clarification_question_requires_core_fields() -> None:
    with pytest.raises(ValidationError):
        SourceClarificationQuestion(
            analysis_run_id="",
            question_text="What measurable impact did this automation have?",
        )

    with pytest.raises(ValidationError):
        SourceClarificationQuestion(
            analysis_run_id="run-1",
            question_text="   ",
        )


def test_source_clarification_message_json_round_trip() -> None:
    message = SourceClarificationMessage(
        question_id="question-1",
        author=ClarificationMessageAuthor.USER,
        message_text="It reduced weekly manual reconciliation.",
    )

    restored = SourceClarificationMessage.model_validate_json(message.model_dump_json())

    assert restored == message
    assert restored.id


def test_source_clarification_message_normalizes_text_fields() -> None:
    message = SourceClarificationMessage(
        question_id="  question-1  ",
        author="user",
        message_text="  It reduced weekly manual reconciliation.  ",
    )

    assert message.question_id == "question-1"
    assert message.author == ClarificationMessageAuthor.USER
    assert message.message_text == "It reduced weekly manual reconciliation."
    assert message.created_at.tzinfo is not None


def test_source_clarification_message_requires_core_fields() -> None:
    with pytest.raises(ValidationError):
        SourceClarificationMessage(
            question_id="",
            author=ClarificationMessageAuthor.USER,
            message_text="It reduced weekly manual reconciliation.",
        )

    with pytest.raises(ValidationError):
        SourceClarificationMessage(
            question_id="question-1",
            author=ClarificationMessageAuthor.USER,
            message_text="   ",
        )


def test_source_clarification_message_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        SourceClarificationMessage(
            question_id="question-1",
            author=ClarificationMessageAuthor.USER,
            message_text="It reduced weekly manual reconciliation.",
            created_at="2026-01-01T00:00:00",
        )


def test_source_finding_json_round_trip() -> None:
    finding = SourceFinding(
        analysis_run_id="run-1",
        role_id="role-1",
        source_id="source-1",
        fact_id="fact-1",
        finding_type=SourceFindingType.SUPPORTS_FACT,
        rationale="The source describes the same automation work.",
        status=SourceFindingStatus.ACCEPTED,
    )

    restored = SourceFinding.model_validate_json(finding.model_dump_json())

    assert restored == finding
    assert restored.id


def test_source_finding_defaults_to_proposed() -> None:
    finding = SourceFinding(
        analysis_run_id="run-1",
        role_id="role-1",
        source_id="source-1",
        finding_type=SourceFindingType.NEW_FACT,
        proposed_fact_text="Led reporting automation for recurring team metrics.",
    )

    assert finding.status == SourceFindingStatus.PROPOSED
    assert finding.created_at.tzinfo is not None
    assert finding.updated_at.tzinfo is not None


def test_source_finding_normalizes_text_fields() -> None:
    finding = SourceFinding(
        analysis_run_id="  run-1  ",
        role_id="  role-1  ",
        source_id="  source-1  ",
        fact_id="  fact-1  ",
        finding_type=SourceFindingType.REVISES_FACT,
        proposed_fact_text="  Revised fact text.  ",
        rationale="  Adds the missing metric.  ",
    )

    assert finding.analysis_run_id == "run-1"
    assert finding.role_id == "role-1"
    assert finding.source_id == "source-1"
    assert finding.fact_id == "fact-1"
    assert finding.proposed_fact_text == "Revised fact text."
    assert finding.rationale == "Adds the missing metric."


def test_source_finding_requires_fact_id_for_fact_comparison_types() -> None:
    for finding_type in (
        SourceFindingType.SUPPORTS_FACT,
        SourceFindingType.REVISES_FACT,
        SourceFindingType.CONTRADICTS_FACT,
        SourceFindingType.DUPLICATES_FACT,
    ):
        with pytest.raises(ValidationError, match="require fact_id"):
            SourceFinding(
                analysis_run_id="run-1",
                role_id="role-1",
                source_id="source-1",
                finding_type=finding_type,
            )


def test_source_finding_requires_proposed_text_for_new_fact() -> None:
    with pytest.raises(ValidationError, match="require proposed_fact_text"):
        SourceFinding(
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-1",
            finding_type=SourceFindingType.NEW_FACT,
        )


def test_source_finding_rejects_fact_id_for_new_fact() -> None:
    with pytest.raises(ValidationError, match="cannot reference"):
        SourceFinding(
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-1",
            fact_id="fact-1",
            finding_type=SourceFindingType.NEW_FACT,
            proposed_fact_text="Led reporting automation for recurring team metrics.",
        )


def test_source_finding_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        SourceFinding(
            analysis_run_id="run-1",
            role_id="role-1",
            source_id="source-1",
            finding_type=SourceFindingType.NEW_FACT,
            proposed_fact_text="Led reporting automation for recurring team metrics.",
            created_at="2026-01-01T00:00:00",
        )
