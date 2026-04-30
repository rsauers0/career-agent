import pytest
from pydantic import ValidationError

from career_agent.errors import InvalidLLMOutputError
from career_agent.experience_roles.models import ExperienceRole
from career_agent.experience_workflow.question_generator import (
    DeterministicSourceQuestionGenerator,
    GeneratedSourceQuestion,
    LLMSourceQuestionGenerator,
)
from career_agent.llm.client import FakeLLMClient
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
    assert generator.generator_name == "deterministic"
    assert questions[0].question_text.startswith("DEV PLACEHOLDER:")
    assert "Senior Systems Analyst at Acme Analytics" in questions[0].question_text
    assert questions[0].relevant_source_ids == ["source-1", "source-2"]
    assert questions[1].relevant_source_ids == ["source-1", "source-2"]


def test_llm_source_question_generator_parses_wrapped_question_json() -> None:
    client = FakeLLMClient(
        response_content="""
        {
          "questions": [
            {
              "question_text": "What measurable impact did this work have?",
              "relevant_source_ids": ["source-1"]
            }
          ]
        }
        """
    )
    generator = LLMSourceQuestionGenerator(client, model="fake-model", temperature=0.1)

    questions = generator.generate_questions(role=build_role(), sources=[build_source("source-1")])

    assert generator.generator_name == "llm"
    assert questions == [
        GeneratedSourceQuestion(
            question_text="What measurable impact did this work have?",
            relevant_source_ids=["source-1"],
        )
    ]
    assert len(client.requests) == 1
    assert client.requests[0].model == "fake-model"
    assert client.requests[0].temperature == 0.1
    assert "Senior Systems Analyst" in client.requests[0].user_prompt
    assert "Source ID: source-1" in client.requests[0].user_prompt


def test_llm_source_question_generator_parses_question_list_json() -> None:
    client = FakeLLMClient(
        response_content="""
        [
          {
            "question_text": "What tools should be captured?",
            "relevant_source_ids": ["source-1"]
          }
        ]
        """
    )
    generator = LLMSourceQuestionGenerator(client)

    questions = generator.generate_questions(role=build_role(), sources=[build_source("source-1")])

    assert len(questions) == 1
    assert questions[0].question_text == "What tools should be captured?"
    assert questions[0].relevant_source_ids == ["source-1"]


def test_llm_source_question_generator_parses_fenced_question_json() -> None:
    client = FakeLLMClient(
        response_content="""
        ```json
        {
          "questions": [
            {
              "question_text": "What outcomes should be clarified?",
              "relevant_source_ids": ["source-1"]
            }
          ]
        }
        ```
        """
    )
    generator = LLMSourceQuestionGenerator(client)

    questions = generator.generate_questions(role=build_role(), sources=[build_source("source-1")])

    assert len(questions) == 1
    assert questions[0].question_text == "What outcomes should be clarified?"
    assert questions[0].relevant_source_ids == ["source-1"]


def test_llm_source_question_generator_rejects_invalid_json() -> None:
    generator = LLMSourceQuestionGenerator(FakeLLMClient(response_content="not json"))

    with pytest.raises(InvalidLLMOutputError, match="valid JSON"):
        generator.generate_questions(role=build_role(), sources=[build_source("source-1")])


def test_llm_source_question_generator_rejects_malformed_question_contract() -> None:
    generator = LLMSourceQuestionGenerator(
        FakeLLMClient(response_content='{"questions": [{"relevant_source_ids": ["source-1"]}]}')
    )

    with pytest.raises(InvalidLLMOutputError, match="source question contract"):
        generator.generate_questions(role=build_role(), sources=[build_source("source-1")])


def test_llm_source_question_generator_rejects_empty_questions() -> None:
    generator = LLMSourceQuestionGenerator(FakeLLMClient(response_content='{"questions": []}'))

    with pytest.raises(InvalidLLMOutputError, match="at least one question"):
        generator.generate_questions(role=build_role(), sources=[build_source("source-1")])


def test_llm_source_question_generator_rejects_unknown_relevant_source_id() -> None:
    generator = LLMSourceQuestionGenerator(
        FakeLLMClient(
            response_content="""
            {
              "questions": [
                {
                  "question_text": "What measurable impact did this work have?",
                  "relevant_source_ids": ["source-2"]
                }
              ]
            }
            """
        )
    )

    with pytest.raises(InvalidLLMOutputError, match="source-2"):
        generator.generate_questions(role=build_role(), sources=[build_source("source-1")])
