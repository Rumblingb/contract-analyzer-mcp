# Contract & Legal Document Analyzer MCP

A zero-external-API MCP server that analyzes, compares, and validates contracts using pure Python NLP and pattern matching. No AI APIs, no external services — runs entirely offline.

> **$19/month** — [Subscribe on Stripe](https://buy.stripe.com/dRm6oJ4Hd2Jugek0wz1oI0m)

---

## Tools

### 1. `analyze_contract(text)`

Extracts and analyzes every major clause in a contract:

| Clause | Extraction Method |
|---|---|
| **Parties** | Preamble regex + entity matching |
| **Effective Date** | Date pattern recognition |
| **Term / Duration** | Term, expiration, duration clauses |
| **Payment Terms** | Amounts, schedules, net terms |
| **Termination** | For cause, without cause, notice periods, survival |
| **Liability Limits** | Caps, indemnification, consequential damages exclusions |
| **Governing Law** | Jurisdiction, venue, applicable law |
| **Non-Compete** | Duration, scope, geography |
| **Non-Solicit** | Duration, scope |
| **Confidentiality** | Definitions, exclusions, survival, return/destruction |
| **Dispute Resolution** | Arbitration, mediation, class action waiver |

Each clause receives a **risk level** — low, medium, or high — based on keyword density and severity heuristics.

### 2. `compare_contracts(text1, text2)`

Diffs two contract versions and flags new risks:

- Line-by-line diff (added, removed, modified lines)
- Risk escalation detection (clauses that went from low→medium or medium→high)
- Change summary statistics

### 3. `extract_obligations(text)`

Lists every obligation in the contract:

- **Action required** — what each party must do
- **Deadlines** — when it must be done
- **Party assignment** — which party is responsible
- **Obligation type** — payment, delivery, performance, reporting, compliance, confidentiality, etc.

### 4. `check_compliance(text, regulation)`

Validates contract against regulatory requirements:

| Regulation | Categories Checked |
|---|---|
| **GDPR** | Data processing basis, subject rights, retention, transfers, DPO, breach notification, DPIA, processor obligations |
| **CCPA** | Consumer rights, notice at collection, sale of data, service provider provisions |
| **SOX** | Internal controls, audit requirements, whistleblower, certification, record retention |
| **SEC** | Registration, disclosure, insider trading, reporting, FCPA |

Returns pass/fail per category plus overall compliance risk rating.

---

## Installation

```bash
pip install 'mcp>=1.0.0'
```

## Usage with Claude Desktop / MCP Clients

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "contract-analyzer": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {}
    }
  }
}
```

### Python Client Example

```python
import asyncio
from mcp import ClientSession, StdioServerParameters

async def main():
    # Connect
    params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )
    async with ClientSession(params) as session:
        # Analyze a contract
        result = await session.call_tool("analyze_contract", {
            "text": "This Agreement is made between Acme Corp and Beta Inc..."
        })
        print(result)

asyncio.run(main())
```

---

## Architecture

```
contract-analyzer-mcp/
├── server.py          # MCP server — all tools + analysis logic
├── requirements.txt   # mcp>=1.0.0
├── smithery.yaml      # MCP server configuration
└── README.md          # This file
```

All analysis is performed via:
- **Regex-based extraction** — dozens of carefully tuned patterns for each clause type
- **Keyword risk scoring** — weighted keyword lists for risk level assignment
- **Python `difflib.Differ`** — for contract comparison
- **Regulatory checklists** — structured compliance matrices

No AI APIs, no network calls, no data leaves your machine.

---

## Pricing

**$19/month** per instance.

[Subscribe Now](https://buy.stripe.com/dRm6oJ4Hd2Jugek0wz1oI0m)

---

## Why This Exists

> Lawyers charge $500+/hour for contract review. Every business deals with contracts. Existing MCP servers do not handle legal document analysis — this is a novel product filling a massive gap.

---

## License

Proprietary — see LICENSE file for details.
