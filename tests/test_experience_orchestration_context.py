import pytest
from pydantic import ValidationError

from career_agent.experience_orchestration.context import AnalysisRunContext


def test_analysis_run_context_normalizes_ids_and_summary() -> None:
    context = AnalysisRunContext(
        analysis_run_id=" run-1 ",
        role_id=" role-1 ",
        source_ids=[" source-1 ", "", "source-2"],
        fact_ids=[" fact-1 "],
        active_constraint_ids=[" constraint-1 "],
        question_ids=[" question-1 "],
        message_ids=[" message-1 "],
        summary=" Test context. ",
    )

    assert context.analysis_run_id == "run-1"
    assert context.role_id == "role-1"
    assert context.source_ids == ["source-1", "source-2"]
    assert context.fact_ids == ["fact-1"]
    assert context.active_constraint_ids == ["constraint-1"]
    assert context.question_ids == ["question-1"]
    assert context.message_ids == ["message-1"]
    assert context.summary == "Test context."


def test_analysis_run_context_requires_source_ids() -> None:
    with pytest.raises(ValidationError):
        AnalysisRunContext(
            analysis_run_id="run-1",
            role_id="role-1",
            source_ids=[],
        )
