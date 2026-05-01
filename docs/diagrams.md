# Architecture Diagrams

This page contains Mermaid diagrams for the current `v2-foundation` architecture.

The diagrams are intentionally focused on implemented boundaries and near-term design direction. They should help explain the project without implying that the future LLM workflow is fully implemented.

## Component Boundaries

```mermaid
flowchart LR
    UserPreferences["User Preferences<br/>Search and matching preferences"]
    ExperienceRoles["Experience Roles<br/>Structured role facts"]
    RoleSources["Role Sources<br/>Raw submitted evidence"]
    SourceAnalysis["Source Analysis<br/>Runs, questions, messages"]
    ExperienceBullets["Experience Bullets<br/>Canonical career bullets"]

    ExperienceRoles -->|"role_id"| RoleSources
    ExperienceRoles -->|"role_id"| SourceAnalysis
    RoleSources -->|"source_ids"| SourceAnalysis
    ExperienceRoles -->|"role_id"| ExperienceBullets
    RoleSources -. "source_ids" .-> ExperienceBullets
    SourceAnalysis -. "future clarification context" .-> ExperienceBullets

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

## Role Source To Bullet Flow

This diagram shows the current deterministic flow from role facts and source material into canonical bullets.

```mermaid
flowchart TD
    Role["Experience Role<br/>employer, title, dates, role_focus"]
    Source["Role Source<br/>raw submitted evidence"]
    BulletService["ExperienceBulletService<br/>validates references"]
    Bullet["Experience Bullet<br/>canonical career data"]

    Role -->|"must exist"| BulletService
    Source -->|"optional source_ids must exist"| BulletService
    BulletService -->|"creates or updates"| Bullet
    Role -->|"role_id"| Source
    Role -->|"role_id"| Bullet
    Source -. "traceability" .-> Bullet
```

## Source Analysis Workflow

Source Analysis stores workflow evidence for clarifying submitted role source material. It does not directly create canonical bullets.

```mermaid
flowchart TD
    Role["Experience Role<br/>structured role facts"]
    Sources["Role Sources<br/>not_analyzed source_ids"]
    Workflow["ExperienceWorkflowService<br/>orchestrates services"]
    ActiveRunGuard["Active Run Guard<br/>one active run per role"]
    Generator["SourceQuestionGenerator<br/>structured question proposals"]
    Run["SourceAnalysisRun<br/>role_id, source_ids, status"]
    Question["SourceClarificationQuestion<br/>analysis_run_id, status"]
    Messages["SourceClarificationMessages<br/>one row per assistant/user/system turn"]
    Resolve["resolve_question / skip_question<br/>explicit approval transition"]

    Role -->|"role_id"| Workflow
    Sources -->|"select only not_analyzed"| Workflow
    Workflow -->|"ensure no active run"| ActiveRunGuard
    Workflow -->|"role + sources"| Generator
    Generator -->|"GeneratedSourceQuestion[]"| Workflow
    Workflow -->|"start run after valid proposals"| Run
    Run -. "only one active run per role_id" .-> Role
    Workflow -->|"save questions through SourceAnalysisService"| Question
    Question -->|"append one message at a time"| Messages
    Messages -. "evidence for closure" .-> Resolve
    Resolve -->|"updates status"| Question
```

The important guardrail is that adding messages does not close a question. A future LLM workflow may decide it is ready to close a question, but it must call an explicit transition that can later include eval approval.

The workflow generates and validates clarification question proposals before it creates the analysis run. This prevents malformed LLM output from creating an active run that blocks later attempts.

## Canonical Data Vs Analysis Artifacts

The future LLM workflow should not freely mutate canonical career data. It should create structured proposals and use deterministic services to apply approved changes.

```mermaid
flowchart LR
    RawEvidence["Raw Evidence<br/>role_sources"]
    RoleFacts["Structured Role Facts<br/>experience_roles"]
    LLMWorkflow["Future LLM Workflow<br/>questions, proposals, evals"]
    AnalysisArtifacts["Analysis Artifacts<br/>source_analysis,<br/>eval results, failed proposals"]
    Services["Deterministic Services<br/>validate and apply changes"]
    CanonicalBullets["Canonical Bullets<br/>experience_bullets"]

    RawEvidence --> LLMWorkflow
    RoleFacts --> LLMWorkflow
    LLMWorkflow --> AnalysisArtifacts
    LLMWorkflow -->|"structured proposal"| Services
    Services -->|"validated write"| CanonicalBullets
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
    Orchestrator["LLM Orchestrator<br/>small structured steps"]
    Constraints["Scoped Constraints<br/>global, role, project, proposal"]
    FactProposals["Experience Fact Proposals<br/>grounded, generic, traceable"]
    Revision["Revision Thread<br/>user + assistant collaboration"]
    Events["FactChangeEvent<br/>actor, event type,<br/>summary, message ids"]
    ApprovedFacts["Approved Experience Facts<br/>canonical evidence"]
    Derived["Derived Evidence<br/>skills, systems, tools,<br/>technologies, capabilities"]
    Tailoring["Future Tailoring<br/>job fit, resumes,<br/>cover letters"]

    RawSources --> Analysis
    Analysis --> Orchestrator
    Constraints --> Orchestrator
    Orchestrator -->|"propose / revise"| FactProposals
    FactProposals --> Revision
    Revision -->|"corrections may create"| Constraints
    Revision -->|"semantic history"| Events
    Revision -->|"approval transition"| ApprovedFacts
    ApprovedFacts -. "changes recorded in" .-> Events
    ApprovedFacts --> Derived
    Derived --> Tailoring
    ApprovedFacts --> Tailoring
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
response classification, constraint extraction, fact proposal, drift checking,
merge checking, and clarification planning. Application services still own
persistence and explicit state transitions.

History has separate responsibilities: messages capture conversational rationale,
change events capture semantic fact/proposal mutations, and snapshots remain
file-level recovery artifacts.

## LLM Boundary

The current LLM boundary has a provider-neutral client protocol plus an opt-in
OpenAI-compatible transport. Model-backed generators depend on this boundary
instead of embedding provider calls directly in workflow services.

```mermaid
flowchart LR
    WorkflowGenerator["LLMSourceQuestionGenerator"]
    Factory["Generator Factory<br/>base URL set = LLM<br/>base URL unset = deterministic"]
    Deterministic["DeterministicSourceQuestionGenerator"]
    LLMClient["LLMClient protocol"]
    FakeClient["FakeLLMClient<br/>test/dev implementation"]
    OpenAIClient["OpenAICompatibleLLMClient<br/>opt-in via configuration"]
    Request["LLMRequest"]
    Response["LLMResponse"]
    Contract["GeneratedSourceQuestion[]<br/>validated JSON contract"]

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

## Current Storage Shape

```mermaid
flowchart TD
    DataDir["CAREER_AGENT_DATA_DIR"]

    DataDir --> Preferences["user_preferences/user_preferences.json"]
    DataDir --> Roles["experience_roles/experience_roles.json"]
    DataDir --> Sources["role_sources/role_sources.json"]
    DataDir --> Bullets["experience_bullets/experience_bullets.json"]
    DataDir --> Analysis["source_analysis/*.json"]
    DataDir --> Snapshots["snapshots/"]

    Snapshots --> PreferenceSnapshots["user_preferences/<timestamp>-user_preferences.json"]
    Snapshots --> RoleSnapshots["experience_roles/<timestamp>-experience_roles.json"]
    Snapshots --> SourceSnapshots["role_sources/<timestamp>-role_sources.json"]
    Snapshots --> BulletSnapshots["experience_bullets/<timestamp>-experience_bullets.json"]
    Snapshots --> AnalysisSnapshots["source_analysis/<timestamp>-*.json"]
```
