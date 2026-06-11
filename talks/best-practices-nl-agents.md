# Best Practices for Natural Language to SQL Agents

## 1. System instruction design

The system instruction is the most impactful factor for SQL accuracy. A vague instruction produces inconsistent queries.

### Include the full schema

Provide the exact table names, column names, column types, and descriptions. The model should never have to guess.

```
| Column | Type | Description |
|--------|------|-------------|
| playerName | STRING | Player full name |
| goalsScored | STRING | Goals scored (use SAFE_CAST to INT64) |
```

### Specify naming conventions

If columns use camelCase, say it explicitly. A model defaulting to snake_case will generate broken queries.

### Add few-shot examples

Include 3-5 representative question/SQL pairs. This anchors the model's behavior far more than general instructions.

```
User: "Who scored the most goals?"
SQL: SELECT playerName, SAFE_CAST(goalsScored AS INT64) AS goals
     FROM `project.dataset.table`
     ORDER BY goals DESC
     LIMIT 10
```

### Define business rules

If "performance rating" or "team style" have specific formulas, write them out. Don't let the model invent its own definitions.

### Specify the query workflow

Tell the agent what to do step by step: discover the schema first, then build the query, then execute. This avoids blind SQL generation.

### Use markdown files, not Python strings

Store system instructions in separate markdown files rather than inline Python strings. This brings several advantages:
- Business teams can read and edit instructions without touching code
- Easier to version, review, and diff in pull requests
- Supports the validation pipeline workflow: edit markdown, run tests, approve, deploy
- The Python code simply loads the file at runtime: `Path("instructions/base.md").read_text()`

Organize instructions by concern and user group:

```
instructions/
├── base.md              # Schema, query workflow, output format
├── business_rules.md    # Formulas, definitions, calculation rules
└── groups/
    ├── group_a.md       # Full access — references full dataset/views
    └── group_b.md       # Restricted access — references restricted views only
```

The agent concatenates `base.md` + `business_rules.md` + the group-specific file at startup. This makes it easy to share common rules while varying access per group.

---

## 2. Query validation

Never blindly execute LLM-generated SQL. Add a validation layer between generation and execution.

### Read-only enforcement

Parse or check the generated SQL to ensure it only contains SELECT statements. Reject any INSERT, UPDATE, DELETE, DROP, ALTER, or TRUNCATE.

### Mandatory LIMIT clause

If the generated query has no LIMIT, append one (e.g., LIMIT 100). This prevents full table scans on large datasets that could be expensive and slow.

### EXPLAIN before execution

Optionally run an EXPLAIN on the query first to estimate cost and catch syntax errors before touching the data.

### Column and table allowlist

Restrict which tables and columns the agent can reference. This prevents accidental access to sensitive data (PII, financial data) that exists in the same dataset.

### Query cost estimation

For cloud data warehouses like BigQuery, use dry-run or estimation APIs to check how much data the query will scan before executing. Set a threshold (e.g., max 1 GB) and reject expensive queries.

---

## 3. Result handling

### Handle empty results gracefully

When a query returns no rows, the agent should reason about why: is the table empty? Is the filter too restrictive? Was a column name wrong? Don't just say "no data found."

### Limit result size

Cap the number of rows returned to the LLM. Sending thousands of rows wastes tokens and degrades response quality. Summarize or paginate if needed.

### Type-aware formatting

Format numbers, dates, and percentages appropriately in the response. Raw database values (e.g., "0.823") are less useful than "82.3% save rate."

---

## 4. Determinism and consistency

### Temperature setting

Use a low temperature (0.0-0.2) for SQL generation. Creativity is not desirable when writing queries.

### Consistent output format

Instruct the agent to always structure its response the same way: a brief interpretation, the data in a readable format (table or list), and optionally the SQL used.

### Idempotent queries

The same question should produce the same SQL. Test this by running the same question multiple times and comparing outputs. Few-shot examples help significantly here.

---

## 5. Testing and evaluation

### Build a test suite of question/expected-result pairs

Create a set of 20-30 representative questions with known correct answers. Run them against the agent after any change to the system instruction, model version, or tools.

Example test cases:
- Simple lookup: "How many players are in the dataset?"
- Filtered query: "Show me the French goalkeepers"
- Aggregation: "What is the average number of goals per team?"
- Ranking: "Top 5 players by assists"
- Comparison: "Compare France and Argentina by goals scored"
- Edge case: "Players with no goals scored" (tests NULL/empty handling)

### Evaluate on multiple dimensions

- **Correctness**: Does the answer match the expected result?
- **SQL validity**: Does the generated SQL parse and execute without errors?
- **Relevance**: Does the response actually answer the question asked?
- **Cost**: How much data was scanned?

### Regression testing

When updating system instructions or switching models, run the full test suite and compare results before and after. This catches regressions early.

---

## 6. System instruction lifecycle management

In production, system instructions evolve over time as business rules change, new tables are added, or edge cases are discovered.

### Version control

Store system instructions in git or a versioned database. Every change should be traceable to a reason and a reviewer.

### Validation pipeline

Before deploying a new system instruction:
1. Run the test suite (section 5) against the new instruction
2. Compare results with the previous version
3. Flag any regressions (questions that previously worked but now fail)
4. Require human approval if regressions are detected

### Business team collaboration

Allow business teams to propose instruction changes (e.g., new business rules, updated column descriptions) via a review interface. The validation pipeline runs automatically, and engineers approve the deployment.

### A/B testing

For critical changes, run both old and new instructions in parallel on real queries. Compare accuracy, latency, and cost before promoting the new version.

---

## 7. Security

### SQL injection prevention

Even though the LLM generates the SQL, treat it as untrusted input. Use parameterized queries where possible, or validate the generated SQL against an allowlist of patterns.

### Data access control

The database credentials used by the agent should have the minimum required permissions: read-only access to specific datasets/tables. Never give the agent admin or write access.

**Never rely on guardrails alone for access control.** Guardrails are LLM-level instructions — the model can ignore them, hallucinate a query to a restricted table, or be prompt-injected into bypassing them. The real security boundary must be enforced at the database level.

Use a **defense in depth** approach with two layers:

| Layer | Purpose | Enforced by |
|-------|---------|-------------|
| Database (views + IAM) | Real access control | Database engine (cannot be bypassed) |
| Guardrails in system instruction | UX optimization, reduce failed queries | LLM (best effort, can be bypassed) |

The guardrails reduce unnecessary failed queries and improve UX (the agent doesn't try to query tables it can't access), but the database layer is what actually enforces security.

### Datasets + authorized views vs row-level access policies

When different user groups need different levels of data access, there are two approaches:

**Datasets + authorized views (recommended for NL-to-SQL agents)**

Create separate datasets with views exposing only the columns and rows each group should see. Each user group's agent uses a service account with read access to its own dataset only.

Advantages:
- The agent sees a different schema per group — it can only query what exists in the view
- Simpler system instructions: just point to the dataset, no need to describe row filters
- The LLM never knows restricted data exists
- Easy to debug: query the view yourself to see exactly what the agent sees

**Row-level access policies**

Same table and schema for everyone, with transparent row-level filtering based on the caller's identity.

Advantages:
- Single schema to maintain
- Better when the difference between groups is which rows they see, not which columns

Disadvantages for NL-to-SQL agents:
- The agent doesn't know why some results are missing, which can lead to confusing responses
- Harder to debug — the same query returns different results depending on who runs it
- More complex to maintain

**Recommendation**: For NL-to-SQL agents with distinct user groups, prefer datasets + authorized views. Each group gets its own system instruction pointing to its own dataset. Clean separation, no ambiguity. Use row-level policies for multi-tenant scenarios where everyone queries the same table but sees only their own rows (e.g., each company sees only its own data).

### Audit logging

Log every query the agent generates and executes, along with the user question, the model used, and the timestamp. This is essential for debugging, compliance, and cost tracking.

### PII handling

If the dataset contains personally identifiable information, instruct the agent to never return raw PII. Apply masking or aggregation rules in the system instruction.

---

## 8. Performance and cost optimization

### Cache frequent queries

If the same questions are asked repeatedly (e.g., "top scorers"), cache the results with a TTL instead of re-querying each time.

### Model selection

Use a smaller/faster model for simple questions (lookups, counts) and a larger model for complex reasoning (multi-table joins, business rule calculations). ADK supports routing to different models.

### Connection management

MCP toolsets maintain persistent connections that can go stale (see Agent Engine limitations). For production, prefer stateless tool implementations or ensure proper connection health checks and reconnection logic.

---

## Summary

| Practice | Impact | Effort |
|----------|--------|--------|
| Full schema in system instruction | High | Low |
| Few-shot examples | High | Low |
| System instructions in markdown files | High | Low |
| Read-only query enforcement | High | Low |
| Mandatory LIMIT clause | Medium | Low |
| Database-level access control (views + IAM) | High | Medium |
| Test suite with known answers | High | Medium |
| Query cost estimation | Medium | Medium |
| System instruction versioning | High | Medium |
| Validation pipeline for instruction changes | High | High |
| A/B testing of instructions | Medium | High |
