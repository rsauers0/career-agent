# Architecture Diagrams

This page contains Mermaid diagrams for the current `v2-foundation` architecture.

The diagrams are intentionally focused on implemented boundaries and near-term design direction. They should help explain the project without implying that the future LLM workflow is fully implemented.

For a database-style view of the JSON records and relationships, see
[Database-Style ER Diagram](er-diagram.md).

## Component Boundaries

```mermaid
flowchart LR
    UserPreferences["User Preferences<br/>Search and matching preferences"]
    ExperienceRoles["Experience Roles<br/>Structured role facts"]
    RoleSources["Role Sources<br/>Raw submitted evidence"]
    SourceAnalysis["Source Analysis<br/>Runs, questions,<br/>messages, findings"]
    ExperienceFacts["Experience Facts<br/>Canonical career facts"]
    ScopedConstraints["Scoped Constraints<br/>Global, role,<br/>and fact guardrails"]
    FactReview["Fact Review<br/>Threads, messages,<br/>and actions"]

    ExperienceRoles -->|"role_id"| RoleSources
    ExperienceRoles -->|"role_id"| SourceAnalysis
    RoleSources -->|"source_ids"| SourceAnalysis
    ExperienceRoles -->|"role_id"| ExperienceFacts
    ExperienceRoles -->|"role scope"| ScopedConstraints
    ExperienceFacts -->|"fact scope"| ScopedConstraints
    ExperienceRoles -->|"role_id"| FactReview
    ExperienceFacts -->|"fact_id"| FactReview
    RoleSources -. "source_ids" .-> ExperienceFacts
    SourceAnalysis -. "findings and evidence context" .-> ExperienceFacts

    UserPreferences -. "future job matching context" .-> ExperienceRoles
```

## Layered Flow

Every current component follows the same foundation pattern.

```mermaid
flowchart TD
    CLI["Typer CLI"]
    Service["Application Service"]
    Repository["JSON Repository"]
    Model["Pydantic Model"]
    Storage["Local JSON Files<br/>CAREER_AGENT_DATA_DIR"]
    Snapshots["Snapshot Files<br/>snapshot-on-overwrite"]

    CLI --> Service
    Service --> Repository
    Repository --> Model
    Repository --> Storage
    Repository --> Snapshots
```

The CLI parses input and renders output. Services own workflow rules. Repositories own local persistence. Pydantic models own validation and JSON serialization.

## Role Source To Fact Flow

This diagram shows the current deterministic flow from role facts and source material into canonical facts.

```mermaid
flowchart TD
    Role["Experience Role<br/>employer, title, dates, role_focus"]
    Source["Role Source<br/>raw submitted evidence"]
    FactService["ExperienceFactService<br/>validates references"]
    Fact["Experience Fact<br/>canonical career data"]

    Role -->|"must exist"| FactService
    Source -->|"optional source_ids must exist"| FactService
    FactService -->|"creates or updates"| Fact
    Role -->|"role_id"| Source
    Role -->|"role_id"| Fact
    Source -. "traceability" .-> Fact
```

## Source Analysis Workflow

Source Analysis stores workflow evidence for clarifying submitted role source material. It does not directly create canonical facts.

```mermaid
flowchart TD
    Role["Experience Role<br/>structured role facts"]
    Sources["Role Sources<br/>not_analyzed source_ids"]
    Workflow["ExperienceWorkflowService<br/>orchestrates services"]
    ActiveRunGuard["Active Run Guard<br/>one active run per role"]
    QuestionGenerator["SourceQuestionGenerator<br/>structured question proposals"]
    FindingGenerator["SourceFindingGenerator<br/>structured finding proposals"]
    Run["SourceAnalysisRun<br/>role_id, source_ids, status"]
    Question["SourceClarificationQuestion<br/>analysis_run_id, status"]
    Messages["SourceClarificationMessages<br/>one row per assistant/user/system turn"]
    Findings["SourceFinding<br/>structured source analysis notes"]
    Apply["apply-findings<br/>accepted findings only"]
    FactService["ExperienceFactService<br/>deterministic fact writes"]
    Facts["ExperienceFact<br/>drafts, revisions,<br/>evidence additions"]
    Resolve["resolve_question / skip_question<br/>explicit approval transition"]
    FindingGate["Finding Gate<br/>no open questions,<br/>no existing findings"]
    Complete["complete run<br/>closed questions,<br/>no accepted unapplied findings"]
    AnalyzedSources["Role Sources<br/>analyzed"]

    Role -->|"role_id"| Workflow
    Sources -->|"select only not_analyzed"| Workflow
    Workflow -->|"ensure no active run"| ActiveRunGuard
    Workflow -->|"role + sources"| QuestionGenerator
    QuestionGenerator -->|"GeneratedSourceQuestion[]"| Workflow
    Workflow -->|"start run after valid proposals"| Run
    Run -. "only one active run per role_id" .-> Role
    Workflow -->|"save questions through SourceAnalysisService"| Question
    Question -->|"append one message at a time"| Messages
    Run -->|"generate-findings"| FindingGate
    Question -->|"resolved or skipped"| FindingGate
    FindingGate -->|"role + sources + questions + messages + facts"| FindingGenerator
    FindingGenerator -->|"GeneratedSourceFinding[]"| Workflow
    Workflow -->|"save findings through SourceAnalysisService"| Findings
    Findings -->|"accepted new_fact / revises_fact / supports_fact"| Apply
    Apply -->|"validated service calls"| FactService
    FactService -->|"draft fact / revision / evidence event"| Facts
    Apply -->|"mark finding applied<br/>with applied_fact_id"| Findings
    Findings -->|"settled enough to close"| Complete
    Question -->|"resolved or skipped"| Complete
    Complete -->|"marks included source_ids"| AnalyzedSources
    Sources -. "supports / revises / contradicts / new_fact" .-> Findings
    Messages -. "evidence for closure" .-> Resolve
    Resolve -->|"updates status"| Question
```

The important guardrail is that adding messages does not close a question. A future LLM workflow may decide it is ready to close a question, but it must call an explicit transition that can later include eval approval.

The workflow generates and validates clarification question proposals before it creates the analysis run. This prevents malformed LLM output from creating an active run that blocks later attempts.

Source findings are structured analysis notes. Accepting a finding records that
the analysis artifact was accepted; canonical fact changes happen only when the
workflow applies accepted findings through `ExperienceFactService`.

Finding generation is blocked while any clarification question for the run is
open, and it is also blocked if findings already exist for the run. The
deterministic finder is only a local validation harness; the LLM-backed finder
performs the real source extraction and classification.

Applying findings is repeat-safe because applied findings move to `applied`
status and record `applied_fact_id`. Unsupported accepted finding types stay as
analysis artifacts and are not automatically canonicalized.

A source analysis run is completed separately after questions are closed and
accepted findings have been applied; completion marks the included role sources
`analyzed`. Archiving an active run closes the run without marking sources
analyzed.

## Canonical Data Vs Analysis Artifacts

The future LLM workflow should not freely mutate canonical career data. It should create structured proposals and use deterministic services to apply approved changes.

```mermaid
flowchart LR
    RawEvidence["Raw Evidence<br/>role_sources"]
    RoleFacts["Structured Role Facts<br/>experience_roles"]
    LLMWorkflow["Future LLM Workflow<br/>questions, proposals, evals"]
    AnalysisArtifacts["Analysis Artifacts<br/>source_analysis,<br/>eval results, failed proposals"]
    Services["Deterministic Services<br/>validate and apply changes"]
    CanonicalFacts["Canonical Facts<br/>experience_facts"]

    RawEvidence --> LLMWorkflow
    RoleFacts --> LLMWorkflow
    LLMWorkflow --> AnalysisArtifacts
    LLMWorkflow -->|"structured proposal"| Services
    Services -->|"validated write"| CanonicalFacts
    Services -. "reject or retain as artifact" .-> AnalysisArtifacts
```

This is the core guardrail model: AI can reason and propose, but application services enforce boundaries before canonical data changes.

## Experience Evidence Normalization Direction

The next workflow stage should normalize source analysis evidence into grounded
experience facts before any persuasive resume or cover-letter writing happens.

```mermaid
flowchart TD
    RawSources["Role Sources<br/>raw evidence"]
    Analysis["Source Analysis<br/>questions and messages"]
    Segments["Source Segments<br/>exact evidence boundaries"]
    Evidence["Source Evidence Items<br/>duties, metrics,<br/>systems, outcomes,<br/>scope qualifiers"]
    Findings["Source Findings<br/>support, revise,<br/>contradict, duplicate,<br/>new, unclear"]
    Orchestrator["Experience Orchestration<br/>route, eval, retry"]
    Constraints["Scoped Constraints<br/>global, role, fact<br/>future scopes later"]
    DraftFacts["Draft Experience Facts<br/>grounded, generic, traceable"]
    Review["Fact Review<br/>threads, messages,<br/>and actions"]
    Events["FactChangeEvent<br/>actor, event type,<br/>summary, message ids"]
    ActiveFacts["Active Experience Facts<br/>canonical evidence,<br/>reference lists"]
    Derived["Derived Evidence Indexes<br/>cross-role skills,<br/>systems, capabilities"]
    Tailoring["Future Tailoring<br/>job fit, resumes,<br/>cover letters"]

    RawSources --> Analysis
    Analysis --> Orchestrator
    Constraints --> Orchestrator
    Orchestrator --> Segments
    Segments --> Evidence
    Evidence --> Findings
    Findings -->|"accepted and applied"| DraftFacts
    DraftFacts --> Review
    Review -->|"corrections may create"| Constraints
    Review -. "message recommendations" .-> Orchestrator
    Review -->|"apply structured action"| ActiveFacts
    ActiveFacts -. "changes recorded in" .-> Events
    ActiveFacts --> Derived
    Derived --> Tailoring
    ActiveFacts --> Tailoring
```

Experience facts are still data normalization. They should use plain,
professional, reusable terminology and must stay grounded in cited source,
question, and message evidence. If evidence is missing, the workflow should ask
for clarification or record missing evidence rather than inventing scope,
metrics, or responsibilities.

Fact merging should be conservative. Similar wording, similar metrics, or shared
tools do not prove that two facts describe the same work. Unclear merges should
remain separate until the user or evidence confirms they belong together.

Future LLM behavior should be orchestrated as narrow checklist steps, such as
source routing, segmentation, evidence extraction, fact comparison, finding
proposal, response classification, constraint extraction, draft fact generation,
drift checking, merge checking, and clarification planning. Application
services still own persistence and explicit state transitions.

History has separate responsibilities: messages capture conversational rationale,
change events capture semantic fact mutations and lifecycle transitions, and
snapshots remain file-level recovery artifacts.

Fact Review messages are workflow evidence. Message recommendations do not
mutate facts by themselves. The action generator can turn review context into
proposed structured actions after loading the target fact, role, messages,
existing actions, and applicable active constraints. Structured review actions
can be applied, but they still call deterministic services for revision,
rejection, activation, evidence updates, and proposed scoped constraint
creation.

No-action generation is valid. It leaves the review thread open and leaves the
fact unchanged, which allows paused or exploratory review conversations to be
resumed later. LLM-generated activation proposals should eventually pass through
an approval/eval flow before application. The current workflow approval boundary
has a dummy implementation that approves for local validation. If a future
approval flow rejects activation, the review action is rejected and the fact
remains unchanged.

## LLM Boundary And Orchestration

The LLM boundary owns provider-neutral completion calls. Experience
Orchestration owns routing, eval/retry behavior, and deterministic service
transitions.

The current LLM boundary has a provider-neutral client protocol plus an opt-in
OpenAI-compatible transport. Model-backed generators depend on this boundary
instead of embedding provider calls directly in workflow services.

```mermaid
flowchart LR
    WorkflowGenerator["LLM Workflow Generators<br/>SourceQuestion + SourceFinding<br/>FactReviewAction"]
    Factory["Generator Factory<br/>base URL set = LLM<br/>base URL unset = deterministic"]
    Deterministic["Deterministic Generators<br/>local validation"]
    LLMClient["LLMClient protocol"]
    FakeClient["FakeLLMClient<br/>test/dev implementation"]
    OpenAIClient["OpenAICompatibleLLMClient<br/>opt-in via configuration"]
    Request["LLMRequest"]
    Response["LLMResponse"]
    Contract["GeneratedSourceQuestion[] / GeneratedSourceFinding[] / GeneratedFactReviewAction[]<br/>validated JSON contracts"]

    Factory --> Deterministic
    Factory --> WorkflowGenerator
    WorkflowGenerator --> Request
    WorkflowGenerator --> LLMClient
    LLMClient --> FakeClient
    LLMClient --> OpenAIClient
    FakeClient --> Response
    OpenAIClient --> Response
    Response --> Contract
```

The planned orchestration layer decomposes source-to-fact analysis into narrow
steps that can work with local or smaller models.

```mermaid
flowchart TD
    Context["AnalysisRunContext<br/>role, sources,<br/>questions, messages,<br/>facts, constraints"]
    Router["Orchestrator Router<br/>classify source/data shape<br/>choose allowed steps"]
    Segmenter["LLM Step<br/>source segmentation"]
    Extractor["LLM Step<br/>evidence extraction"]
    Comparator["LLM Step<br/>fact comparison"]
    Proposer["LLM Step<br/>finding proposal"]
    Eval["Eval Steps<br/>schema, references,<br/>metrics, scope,<br/>merge safety, drift"]
    Retry["Structured RetryRequest<br/>failed checks + excerpts<br/>revision rules"]
    HumanReview["Needs Human Review<br/>persist failure artifact"]
    Services["Deterministic Services<br/>SourceAnalysisService<br/>ExperienceFactService"]
    Artifacts["Analysis Artifacts<br/>SourceSegment<br/>SourceEvidenceItem<br/>SourceFinding"]
    Facts["ExperienceFact<br/>canonical data"]

    Context --> Router
    Router --> Segmenter
    Segmenter --> Eval
    Eval -->|"pass"| Extractor
    Eval -->|"fail, retry budget remains"| Retry
    Retry --> Segmenter
    Eval -->|"fail, retry exhausted"| HumanReview
    Extractor --> Eval
    Eval -->|"pass"| Comparator
    Comparator --> Eval
    Eval -->|"pass"| Proposer
    Proposer --> Eval
    Eval -->|"accepted proposal"| Services
    Services --> Artifacts
    Services -->|"only deterministic apply"| Facts
```

The orchestration rule is: LLM components analyze and propose, eval components
critique and validate, orchestrators route and retry, and domain services
persist and enforce deterministic rules.

## Current Storage Shape

```mermaid
flowchart TD
    DataDir["CAREER_AGENT_DATA_DIR"]

    DataDir --> Preferences["user_preferences/user_preferences.json"]
    DataDir --> Roles["experience_roles/experience_roles.json"]
    DataDir --> Sources["role_sources/role_sources.json"]
    DataDir --> Facts["experience_facts/experience_facts.json"]
    DataDir --> FactEvents["experience_facts/fact_change_events.json"]
    DataDir --> Constraints["scoped_constraints/scoped_constraints.json"]
    DataDir --> Review["fact_review/*.json"]
    DataDir --> Analysis["source_analysis/*.json"]
    DataDir --> Snapshots["snapshots/"]

    Snapshots --> PreferenceSnapshots["user_preferences/<timestamp>-user_preferences.json"]
    Snapshots --> RoleSnapshots["experience_roles/<timestamp>-experience_roles.json"]
    Snapshots --> SourceSnapshots["role_sources/<timestamp>-role_sources.json"]
    Snapshots --> FactSnapshots["experience_facts/<timestamp>-experience_facts.json"]
    Snapshots --> FactEventSnapshots["experience_facts/<timestamp>-fact_change_events.json"]
    Snapshots --> ConstraintSnapshots["scoped_constraints/<timestamp>-scoped_constraints.json"]
    Snapshots --> ReviewSnapshots["fact_review/<timestamp>-*.json"]
    Snapshots --> AnalysisSnapshots["source_analysis/<timestamp>-*.json"]
```
