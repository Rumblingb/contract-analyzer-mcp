#!/usr/bin/env python3
"""Contract & Legal Document Analyzer MCP — AI-powered contract review without external APIs."""

import json, re, datetime
from mcp.server import Server, stdio_server

server = Server("contract-analyzer-mcp")

# ─── Pattern dictionaries ─────────────────────────────────────────────────────

PARTY_PATTERNS = [
    (r'(?:between|by and between)\s+([A-Z][A-Za-z0-9\s,.]+?)(?:\s+\(?"(?:hereinafter|the)\s+"?([^"]+)"?)?', 2),
    (r'([A-Z][A-Za-z0-9\s,.]+?)\s+\(?"(?:hereinafter|the)\s+"?([^"]+)"?', 2),
    (r'"([^"]+)"\s+\(+?(?:hereinafter|the)\s+"?([^"]+)"?\)?', 2),
]

DATE_PATTERNS = [
    r'effective\s+(?:as\s+of|date)[:\s]+([A-Z][a-z]+ \d{1,2},?\s*\d{4})',
    r'this\s+\d{1,2}(?:st|nd|rd|th)\s+day\s+of\s+([A-Z][a-z]+),\s*(\d{4})',
    r'dated\s+(?:as\s+of\s+)?([A-Z][a-z]+ \d{1,2},?\s*\d{4})',
]

TERM_PATTERNS = [
    (r'term\s+(?:of|shall\s+be)\s+(\d+)\s*(month|year|day)s?', "duration"),
    (r'initial\s+term\s+(?:of\s+)?(\d+)\s*(month|year|day)s?', "initial"),
    (r'renew(?:al)?\s+(?:automatically|shall\s+renew)(?:\s+for\s+(\d+)\s*(month|year|day)s?)?', "renewal"),
    (r'commenc(?:e|ing)\s+(?:on\s+)?([A-Z][a-z]+ \d{1,2},?\s*\d{4})', "start"),
    (r'expir(?:e|ation|y)\s+(?:on\s+)?([A-Z][a-z]+ \d{1,2},?\s*\d{4})', "end"),
]

MONEY_PATTERNS = [
    r'\$([\d,]+(?:\.\d{2})?)\s*(?:per\s+(?:month|year|annum)|monthly|annually|a\s+year)',
    r'(?:payment|fee|compensation|salary|rate)[:\s]*\$?([\d,]+(?:\.\d{2})?)',
]

OBLIGATION_PATTERNS = [
    r'shall\s+(?:provide|deliver|submit|pay|maintain|ensure|obtain|notify|indemnify|defend|hold|keep|make|perform|execute|file|report)[^.]*\.',
    r'must\s+(?:provide|deliver|submit|pay|maintain|ensure|obtain|notify)[^.]*\.',
    r'agrees?\s+to\s+(?:provide|deliver|submit|pay|maintain|ensure|obtain|notify|indemnify|defend)[^.]*\.',
    r'covenant[^.]*\.',
    r'warrant[^.]*\.',
    r'represent[^.]*\.',
]

TERMINATION_PATTERNS = {
    "for_cause": r'terminat(?:e|ion)\s+(?:for|upon|in\s+the\s+event\s+of)\s+(?:cause|breach|default|material\s+breach)',
    "without_cause": r'terminat(?:e|ion)\s+(?:without|at\s+will|for\s+convenience|without\s+cause)',
    "notice_period": r'(\d+)\s*(?:day|month|year)s?\s+(?:prior\s+)?(?:written\s+)?notice',
    "automatic": r'automatic(?:ally)?\s+terminat',
}

RISK_TERMS = {
    "high": ["indemnify", "indemnification", "hold harmless", "joint and several", "unlimited liability",
             "irrevocable", "non-refundable", "sole discretion", "binding arbitration",
             "no right to", "waive", "forfeiture", "penalty", "confidentiality", "non-compete",
             "exclusive jurisdiction", "forum", "severance"],
    "medium": ["reasonable efforts", "best efforts", "material adverse", "subject to",
               "except as", "to the extent", "including but not limited to",
               "time is of the essence", "liquidated damages", "liquidateddamages"],
}

@server.tool(
    name="contract_analyze",
    description="Analyze a contract document for key terms, parties, dates, obligations, and risk levels.",
    input_schema={
        "type": "object",
        "properties": {
            "contract_text": {"type": "string", "description": "Full text of the contract/agreement"},
            "document_type": {"type": "string", "enum": ["auto", "employment", "service", "nda", "lease", "license", "other"],
                             "description": "Type of document", "default": "auto"}
        },
        "required": ["contract_text"]
    }
)
async def contract_analyze(contract_text: str, document_type: str = "auto") -> str:
    try:
        text = contract_text
        result = {
            "document_type": document_type,
            "parties": [],
            "dates": {},
            "terms": {},
            "payment": {},
            "obligations": [],
            "termination": {},
            "risks": [],
            "clause_summary": {},
        }
        
        # Extract parties
        parties_found = set()
        for pattern, group_count in PARTY_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if group_count == 2:
                    name, alias = match.group(1).strip(), match.group(2).strip() if match.lastindex >= 2 else ""
                    parties_found.add(name)
                    if alias:
                        parties_found.add(f"{name} (\"{alias}\")")
                else:
                    name = match.group(1).strip()
                    parties_found.add(name)
        result["parties"] = list(parties_found)[:10]
        
        # Extract dates
        for pattern in DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.lastindex >= 2:
                    result["dates"]["effective"] = f"{match.group(1)} {match.group(2)}"
                else:
                    result["dates"]["effective"] = match.group(1)
                break
        
        # Extract term
        for pattern, key in TERM_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if key in ("duration", "initial"):
                    result["terms"]["term"] = f"{match.group(1)} {match.group(2)}(s)"
                elif key == "renewal":
                    renewal = f"Auto-renewal" + (f" for {match.group(1)} {match.group(2)}(s)" if match.lastindex >= 1 else "")
                    result["terms"]["renewal"] = renewal
                elif key in ("start", "end"):
                    result["terms"][key] = match.group(1)
        
        # Extract payment
        for pattern in MONEY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["payment"]["amount"] = f"${match.group(1)}"
                context = text[max(0, match.start()-30):match.end()+30].strip()
                result["payment"]["context"] = context[:100]
                break
        
        # Extract obligations
        obligations = []
        for pattern in OBLIGATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                obl = match.group(0).strip()
                if len(obl) > 20:
                    obligations.append(obl[:200])
        result["obligations"] = obligations[:15]
        
        # Termination analysis
        for key, pattern in TERMINATION_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["termination"][key] = True
                context = text[max(0, match.start()-20):match.end()+50].strip()
                if key == "notice_period":
                    result["termination"]["notice_period_days"] = match.group(1)
        
        # Risk assessment
        risks = []
        for severity, terms in RISK_TERMS.items():
            for term in terms:
                idx = text.lower().find(term)
                if idx >= 0:
                    context = text[max(0, idx-30):idx+len(term)+30].strip()
                    risks.append({
                        "term": term,
                        "severity": severity,
                        "context": context[:120],
                        "recommendation": "Review carefully" if severity == "high" else "Verify scope"
                    })
        result["risks"] = risks[:20]
        
        # Overall risk score
        high_risks = sum(1 for r in risks if r["severity"] == "high")
        med_risks = sum(1 for r in risks if r["severity"] == "medium")
        if high_risks > 5:
            result["overall_risk"] = "HIGH"
        elif high_risks > 2 or med_risks > 5:
            result["overall_risk"] = "MEDIUM"
        else:
            result["overall_risk"] = "LOW"
        
        result["summary"] = f"Found {len(result['parties'])} parties, {len(result['obligations'])} obligations, {len(risks)} risk items. Overall risk: {result['overall_risk']}."
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "isError": True}, indent=2)

@server.tool(
    name="contract_compare",
    description="Compare two versions of a contract and highlight changes.",
    input_schema={
        "type": "object",
        "properties": {
            "original_text": {"type": "string", "description": "Original contract text"},
            "modified_text": {"type": "string", "description": "Modified/proposed contract text"}
        },
        "required": ["original_text", "modified_text"]
    }
)
async def contract_compare(original_text: str, modified_text: str) -> str:
    try:
        orig_sentences = set(re.split(r'(?<=[.!?])\s+', original_text))
        mod_sentences = set(re.split(r'(?<=[.!?])\s+', modified_text))
        
        added = mod_sentences - orig_sentences
        removed = orig_sentences - mod_sentences
        
        return json.dumps({
            "changes_summary": f"{len(added)} sentences added, {len(removed)} sentences removed",
            "added_sentences": list(added)[:20],
            "removed_sentences": list(removed)[:20],
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "isError": True}, indent=2)

@server.tool(
    name="contract_check_compliance",
    description="Check a contract for compliance with regulations like GDPR, CCPA, SOX.",
    input_schema={
        "type": "object",
        "properties": {
            "contract_text": {"type": "string", "description": "Contract text to check"},
            "regulation": {"type": "string", "enum": ["gdpr", "ccpa", "sox", "hipaa", "general"],
                          "default": "general"}
        },
        "required": ["contract_text"]
    }
)
async def contract_check_compliance(contract_text: str, regulation: str = "general") -> str:
    try:
        text = contract_text.lower()
        checks = []
        
        if regulation in ("gdpr", "general"):
            gdpr_checks = [
                ("Data processing terms", "data processing" in text or "process" in text),
                ("Data retention policy", "retention" in text or "delete" in text or "destroy" in text),
                ("Data breach notification", "breach" in text or "notification" in text),
                ("Cross-border transfer", "transfer" in text and "data" in text),
                ("GDPR compliance mention", "gdpr" in text),
                ("Data Protection Officer", "data protection officer" in text or "dpo" in text),
            ]
            checks.extend([{"check": c, "found": f, "status": "PASS" if f else "FAIL"} for c, f in gdpr_checks])
        
        if regulation in ("ccpa", "general"):
            ccpa_checks = [
                ("Consumer data rights", "consumer" in text and "right" in text),
                ("Opt-out mechanism", "opt-out" in text or "opt out" in text),
                ("Data deletion rights", "deletion" in text or "delete" in text),
                ("Non-discrimination", "discrimination" in text),
            ]
            checks.extend([{"check": c, "found": f, "status": "PASS" if f else "FAIL"} for c, f in ccpa_checks])
        
        if regulation in ("sox", "general"):
            sox_checks = [
                ("Internal controls", "control" in text or "internal control" in text),
                ("Audit trail", "audit" in text),
                ("Record retention", "record" in text and "retention" in text),
                ("Financial reporting", "financial" in text or "report" in text),
            ]
            checks.extend([{"check": c, "found": f, "status": "PASS" if f else "FAIL"} for c, f in sox_checks])
        
        pass_count = sum(1 for c in checks if c["status"] == "PASS")
        return json.dumps({
            "regulation": regulation.upper(),
            "compliance_score": f"{pass_count}/{len(checks)}",
            "checks": checks,
            "recommendation": "Review with legal counsel" if pass_count < len(checks) else "Compliance requirements appear addressed"
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "isError": True}, indent=2)

def main():
    import anyio
    async def run():
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())
    anyio.run(run)

if __name__ == "__main__":
    main()
