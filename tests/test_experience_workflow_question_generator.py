import pytest
from pydantic import ValidationError

from career_agent.experience_roles.models import ExperienceRole
from career_agent.experience_workflow.question_generator import (
    DeterministicSourceQuestionGenerator,
    GeneratedSourceQuestion,
)
from career_agent.role_sources.models import RoleSourceEntry


def build_role() -> ExperienceRole:
    return ExperienceRole(
        id="role-1",
        employer_name="Acme Analytics",
        job_title="Senior Systems Analyst",
        start_date="05/2021",
        end_date="06/2024",
    )


def build_source(source_id: str = "source-1") -> RoleSourceEntry:
    return RoleSourceEntry(
        id=source_id,
        role_id="role-1",
        source_text="- Led a reporting automation project.",
    )


def test_generated_source_question_normalizes_fields() -> None:
    question = GeneratedSourceQuestion(
        question_text="  What measurable impact should be clarified?  ",
        relevant_source_ids=["  source-1  ", "", "  source-2  "],
    )

    assert question.question_text == "What measurable impact should be clarified?"
    assert question.relevant_source_ids == ["source-1", "source-2"]


def test_generated_source_question_requires_question_text() -> None:
    with pytest.raises(ValidationError):
        GeneratedSourceQuestion(question_text="   ")


def test_deterministic_source_question_generator_uses_role_and_sources() -> None:
    generator = DeterministicSourceQuestionGenerator()

    questions = generator.generate_questions(
        role=build_role(),
        sources=[build_source("source-1"), build_source("source-2")],
    )

    assert len(questions) == 2
    assert questions[0].question_text.startswith("DEV PLACEHOLDER:")
    assert "Senior Systems Analyst at Acme Analytics" in questions[0].question_text
    assert questions[0].relevant_source_ids == ["source-1", "source-2"]
    assert questions[1].relevant_source_ids == ["source-1", "source-2"]
