# AI WORKSPACE — OPERATOR GUIDE
> For: Finn (Human Orchestrator)
> System: 7-agent multi-agent development pipeline

---

## Your Job
You are the CEO. You give direction, approve handoffs, and make judgment calls.
The agents do the work. You do not code, document, or test anything unless you choose to.

---

## The Agents & Where They Live

| # | Agent | Model | Tool | Owns |
|---|-------|-------|------|------|
| 0 | Designer | Opus | Regular web tab | /specs/design_brief.md |
| 1 | Product Manager | Sonnet | Regular web tab | /specs, /tasks |
| 2 | Architect | Opus | Regular web tab | /architecture |
| 3 | Developer | Opus/Sonnet | Claude Code tab | /src |
| 4 | QA Engineer | Sonnet | Claude Code tab | /tests, qa_report |
| 5 | Reviewer | Opus | Claude Code tab | review_decision |
| 6 | Docs Writer | Sonnet | Regular web tab | /docs |

### Why This Split
Regular web tabs are better for conversational, document-focused agents (Designer, PM, Architect, Docs) — they involve discussion with you and producing written specs.
Claude Code tabs are better for agents that need to read and write actual code files directly (Developer, QA, Reviewer).
All agents CAN run in Claude Code if preferred — this is just the optimal setup.

---

## The Two-Phase Workflow

### Phase 0 — Design & Discovery (Before the main pipeline)
This happens FIRST, before any other agent is involved.
```
You (your idea, in plain language)
  → Designer Agent (brainstorm with you → produces design_brief.md)
  → You review and approve the design brief
  → Hand design_brief.md to PM Agent to begin Phase 1
```
The Designer is your creative and strategic thinking partner. You talk through the product with them freely. They synthesize the conversation into a structured brief that the PM can act on.

### Phase 1 — Full Development Pipeline
```
PM Agent (reads design_brief → writes PRD + user stories + Asana tasks)
  → Architect Agent (reads PRD → writes system blueprint)
  → Developer Agent (reads blueprint + task → writes code)
  → QA Agent (reads code + user story → tests + QA report)
  → Reviewer Agent (reads QA report + code → approves or revises)
  → Docs Agent (reads approved code → writes documentation)
  → Asana task marked Complete
```

---

## How to Start Any Agent Session
1. Open the appropriate tab type (web or Claude Code — see table above)
2. Paste the full contents of the agent's prompt file from /agents/prompts/
3. Each prompt file has a **"What to Send This Agent"** section at the top — follow it exactly for that agent
4. For Claude Code agents (Developer, QA, Reviewer): point Claude Code at the project folder instead of pasting files
5. Agent self-directs from there, referencing the task queue and shared files

### Starting the Designer (First Time)
The Designer prompt file already contains context about this workspace system.
Simply paste the prompt and start describing your tool idea in plain language.
Have a real conversation — don't worry about being structured. The Designer's job is to structure it for you.

---

## Folder Reference

```
/ai-workspace
  README.md            ← This file. Your operator manual.
  MASTER_LOG.md        ← Every agent reads and writes here. The system's memory.
  /agents/prompts/     ← System prompts for each agent (paste to start a session)
  /specs/              ← design_brief, PRD, user stories
  /architecture/       ← System design docs
  /tasks/              ← task_queue.md
  /src/                ← All application code
  /tests/              ← All test files
  /reports/            ← dev_log, qa_report, review_decision
  /docs/               ← All documentation
  /logs/               ← Reserved for Python orchestration later
```

---

## Asana Integration
- Project: https://app.asana.com/1/1213387246493600/project/1213387271165917/list/1213387297952178
- Every feature = one Asana task with subtasks: Design, Arch, Dev, QA, Review, Docs
- Agents update Asana directly via MCP connection
- You monitor progress in Asana without opening files

---

## When Things Go Wrong
- Agent produces something unexpected → read MASTER_LOG.md for context drift
- Two agents contradict each other → Architect wins on structure, PM wins on requirements, Designer wins on product intent
- Agent gets stuck → paste the relevant files directly into the chat and ask it to continue

---

## Adding Python Orchestration Later
When you're ready to automate handoffs, the /logs folder and MASTER_LOG.md are already structured for a Python script to parse and trigger the next agent automatically. Ask the Developer agent to build this when the time comes.
