import pytest
from pydantic import ValidationError

from career_agent.errors import InvalidLLMOutputError
from career_agent.experience_facts.models import ExperienceFact
from career_agent.experience_roles.models import ExperienceRole
from career_agent.experience_workflow.finding_generator import (
    DeterministicSourceFindingGenerator,
    GeneratedSourceFinding,
    LLMSourceFindingGenerator,
)
from career_agent.llm.client import FakeLLMClient
from career_agent.role_sources.models import RoleSourceEntry
from career_agent.source_analysis.models import (
    ClarificationMessageAuthor,
    SourceClarificationMessage,
    SourceClarificationQuestion,
    SourceClarificationQuestionStatus,
    SourceFindingType,
)


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


def build_question() -> SourceClarificationQuestion:
    return SourceClarificationQuestion(
        id="question-1",
        analysis_run_id="run-1",
        question_text="What measurable impact did this work have?",
        relevant_source_ids=["source-1"],
        status=SourceClarificationQuestionStatus.RESOLVED,
    )


def build_message() -> SourceClarificationMessage:
    return SourceClarificationMessage(
        id="message-1",
        question_id="question-1",
        author=ClarificationMessageAuthor.USER,
        message_text="It reduced weekly reporting time.",
    )


def build_fact(fact_id: str = "fact-1") -> ExperienceFact:
    return ExperienceFact(
        id=fact_id,
        role_id="role-1",
        source_ids=["source-1"],
        text="Led a reporting automation project.",
    )


def test_generated_source_finding_normalizes_fields() -> None:
    finding = GeneratedSourceFinding(
        source_id="  source-1  ",
        finding_type=SourceFindingType.NEW_FACT,
        proposed_fact_text="  Led reporting automation.  ",
        rationale="  Supported by the source.  ",
    )

    assert finding.source_id == "source-1"
    assert finding.proposed_fact_text == "Led reporting automation."
    assert finding.rationale == "Supported by the source."


def test_generated_source_finding_requires_fact_id_for_fact_comparison_types() -> None:
    for finding_type in (
        SourceFindingType.SUPPORTS_FACT,
        SourceFindingType.REVISES_FACT,
        SourceFindingType.CONTRADICTS_FACT,
        SourceFindingType.DUPLICATES_FACT,
    ):
        with pytest.raises(ValidationError, match="require fact_id"):
            GeneratedSourceFinding(
                source_id="source-1",
                finding_type=finding_type,
            )


def test_generated_source_finding_requires_proposed_text_for_new_fact() -> None:
    with pytest.raises(ValidationError, match="require proposed_fact_text"):
        GeneratedSourceFinding(
            source_id="source-1",
            finding_type=SourceFindingType.NEW_FACT,
        )


def test_deterministic_source_finding_generator_returns_unclear_placeholders() -> None:
    generator = DeterministicSourceFindingGenerator()

    findings = generator.generate_findings(
        role=build_role(),
        sources=[build_source("source-1"), build_source("source-2")],
        questions=[],
        messages=[],
        facts=[],
    )

    assert generator.generator_name == "deterministic"
    assert len(findings) == 2
    assert findings[0].source_id == "source-1"
    assert findings[0].finding_type == SourceFindingType.UNCLEAR
    assert "Deterministic placeholder" in (findings[0].rationale or "")
    assert findings[1].source_id == "source-2"


def test_llm_source_finding_generator_parses_wrapped_finding_json() -> None:
    client = FakeLLMClient(
        response_content="""
        {
          "findings": [
            {
              "source_id": "source-1",
              "finding_type": "supports_fact",
              "fact_id": "fact-1",
              "proposed_fact_text": null,
              "rationale": "The source describes the same automation work."
            }
          ]
        }
        """
    )
    generator = LLMSourceFindingGenerator(client, model="fake-model", temperature=0.1)

    findings = generator.generate_findings(
        role=build_role(),
        sources=[build_source("source-1")],
        questions=[build_question()],
        messages=[build_message()],
        facts=[build_fact("fact-1")],
    )

    assert generator.generator_name == "llm"
    assert findings == [
        GeneratedSourceFinding(
            source_id="source-1",
            finding_type=SourceFindingType.SUPPORTS_FACT,
            fact_id="fact-1",
            rationale="The source describes the same automation work.",
        )
    ]
    assert len(client.requests) == 1
    assert client.requests[0].model == "fake-model"
    assert client.requests[0].temperature == 0.1
    assert "Senior Systems Analyst" in client.requests[0].user_prompt
    assert "Source ID: source-1" in client.requests[0].user_prompt
    assert "Fact ID: fact-1" in client.requests[0].user_prompt


def test_llm_source_finding_generator_parses_finding_list_json() -> None:
    client = FakeLLMClient(
        response_content="""
        [
          {
            "source_id": "source-1",
            "finding_type": "new_fact",
            "fact_id": null,
            "proposed_fact_text": "Led reporting automation for recurring team metrics.",
            "rationale": "The source states this distinct work directly."
          }
        ]
        """
    )
    generator = LLMSourceFindingGenerator(client)

    findings = generator.generate_findings(
        role=build_role(),
        sources=[build_source("source-1")],
        questions=[],
        messages=[],
        facts=[],
    )

    assert len(findings) == 1
    assert findings[0].finding_type == SourceFindingType.NEW_FACT
    assert findings[0].proposed_fact_text == "Led reporting automation for recurring team metrics."


def test_llm_source_finding_generator_parses_fenced_finding_json() -> None:
    client = FakeLLMClient(
        response_content="""
        ```json
        {
          "findings": [
            {
              "source_id": "source-1",
              "finding_type": "unclear",
              "fact_id": null,
              "proposed_fact_text": null,
              "rationale": "The source appears to contain multiple items."
            }
          ]
        }
        ```
        """
    )
    generator = LLMSourceFindingGenerator(client)

    findings = generator.generate_findings(
        role=build_role(),
        sources=[build_source("source-1")],
        questions=[],
        messages=[],
        facts=[],
    )

    assert len(findings) == 1
    assert findings[0].finding_type == SourceFindingType.UNCLEAR


def test_llm_source_finding_generator_rejects_invalid_json() -> None:
    generator = LLMSourceFindingGenerator(FakeLLMClient(response_content="not json"))

    with pytest.raises(InvalidLLMOutputError, match="valid JSON"):
        generator.generate_findings(
            role=build_role(),
            sources=[build_source("source-1")],
            questions=[],
            messages=[],
            facts=[],
        )


def test_llm_source_finding_generator_rejects_malformed_contract() -> None:
    generator = LLMSourceFindingGenerator(
        FakeLLMClient(response_content='{"findings": [{"source_id": "source-1"}]}')
    )

    with pytest.raises(InvalidLLMOutputError, match="source finding contract"):
        generator.generate_findings(
            role=build_role(),
            sources=[build_source("source-1")],
            questions=[],
            messages=[],
            facts=[],
        )


def test_llm_source_finding_generator_rejects_empty_findings() -> None:
    generator = LLMSourceFindingGenerator(FakeLLMClient(response_content='{"findings": []}'))

    with pytest.raises(InvalidLLMOutputError, match="at least one finding"):
        generator.generate_findings(
            role=build_role(),
            sources=[build_source("source-1")],
            questions=[],
            messages=[],
            facts=[],
        )


def test_llm_source_finding_generator_rejects_unknown_source_id() -> None:
    generator = LLMSourceFindingGenerator(
        FakeLLMClient(
            response_content="""
            {
              "findings": [
                {
                  "source_id": "source-2",
                  "finding_type": "unclear",
                  "fact_id": null,
                  "proposed_fact_text": null,
                  "rationale": "Unknown source."
                }
              ]
            }
            """
        )
    )

    with pytest.raises(InvalidLLMOutputError, match="source-2"):
        generator.generate_findings(
            role=build_role(),
            sources=[build_source("source-1")],
            questions=[],
            messages=[],
            facts=[],
        )


def test_llm_source_finding_generator_rejects_unknown_fact_id() -> None:
    generator = LLMSourceFindingGenerator(
        FakeLLMClient(
            response_content="""
            {
              "findings": [
                {
                  "source_id": "source-1",
                  "finding_type": "supports_fact",
                  "fact_id": "fact-2",
                  "proposed_fact_text": null,
                  "rationale": "Unknown fact."
                }
              ]
            }
            """
        )
    )

    with pytest.raises(InvalidLLMOutputError, match="fact-2"):
        generator.generate_findings(
            role=build_role(),
            sources=[build_source("source-1")],
            questions=[],
            messages=[],
            facts=[build_fact("fact-1")],
        )


def test_llm_source_finding_generator_rejects_duplicate_findings() -> None:
    generator = LLMSourceFindingGenerator(
        FakeLLMClient(
            response_content="""
            {
              "findings": [
                {
                  "source_id": "source-1",
                  "finding_type": "unclear",
                  "fact_id": null,
                  "proposed_fact_text": null,
                  "rationale": "First."
                },
                {
                  "source_id": "source-1",
                  "finding_type": "unclear",
                  "fact_id": null,
                  "proposed_fact_text": null,
                  "rationale": "Second."
                }
              ]
            }
            """
        )
    )

    with pytest.raises(InvalidLLMOutputError, match="duplicate"):
        generator.generate_findings(
            role=build_role(),
            sources=[build_source("source-1")],
            questions=[],
            messages=[],
            facts=[],
        )
