"""Quick validation test for Contract Analyzer MCP."""
import json, sys, os
sys.path.insert(0, '/mnt/d/Projects/pickaxes/contract-analyzer-mcp')
os.chdir('/mnt/d/Projects/pickaxes/contract-analyzer-mcp')

from server import (
    analyze_contract_internal, extract_obligations_internal,
    check_compliance_internal, diff_texts, flag_new_risks,
)

SAMPLE = """MASTER SERVICES AGREEMENT

This Master Services Agreement is made as of January 15, 2025,
by and between Acme Corporation, a Delaware corporation,
and Beta Solutions LLC, a California limited liability company.

1. TERM. The initial term of this Agreement shall be two (2) years.

2. PAYMENT TERMS. Client shall pay a monthly fee of $5,000. Invoices are Net 30.

3. CONFIDENTIALITY. Each party shall maintain confidentiality for 3 years.

4. NON-COMPETE. For 1 year, Provider shall not compete within North America.

5. NON-SOLICIT. For 12 months, Provider shall not solicit employees or customers.

6. LIMITATION OF LIABILITY. Aggregate liability shall not exceed total fees paid.
   Neither party liable for consequential damages.

7. TERMINATION. Either party may terminate for cause with 30 day cure period.
   Either party may terminate without cause with 90 days notice.

8. GOVERNING LAW. Governed by laws of State of New York.

9. DISPUTE RESOLUTION. Binding arbitration by AAA in New York.

10. INDEMNIFICATION. Provider shall indemnify Client.
"""

SAMPLE2 = SAMPLE.replace(
    'Aggregate liability shall not exceed total fees paid.',
    'Provider liability shall not exceed $50,000. Client liability unlimited.'
).replace(
    'either party provides',
    'Client provides'
)

errors = []

# TEST 1: analyze_contract
print("=== TEST 1: analyze_contract ===")
r = analyze_contract_internal(SAMPLE)
parties = r['clauses']['parties']['value']
print(f"  Parties found: {len(parties)}")
if len(parties) > 0:
    print(f"  Party names: {[p['name'] for p in parties]}")
else:
    errors.append("No parties extracted")
print(f"  Effective date: {r['clauses']['effective_date']['value']}")
print(f"  Overall risk: {r['risk_summary']['overall_risk']}")
print(f"  Risk counts: {r['risk_summary']['risk_counts']}")

# TEST 2: compare_contracts
print("\n=== TEST 2: compare_contracts ===")
changes = diff_texts(SAMPLE, SAMPLE2)
risks = flag_new_risks(SAMPLE, SAMPLE2)
print(f"  Total changes: {len(changes)}")
print(f"  New risks: {len(risks)}")
if risks:
    for nr in risks:
        print(f"    {nr['clause']}: {nr['old_risk']} -> {nr['new_risk']}")

# TEST 3: extract_obligations
print("\n=== TEST 3: extract_obligations ===")
obs = extract_obligations_internal(SAMPLE)
print(f"  Parties: {obs['parties_identified']}")
print(f"  Total obligations: {obs['total_obligations']}")
for p, plist in obs['obligations'].items():
    print(f"    {p}: {len(plist)} obligations")
    for ob in plist[:2]:
        print(f"      [{ob['type']}] {ob['action'][:70]}")

# TEST 4-7: compliance
for reg in ['gdpr', 'ccpa', 'sox', 'sec']:
    print(f"\n=== TEST 4: check_compliance ({reg.upper()}) ===")
    c = check_compliance_internal(SAMPLE, reg)
    print(f"  Compliant: {c['compliant']}, Risk: {c['overall_risk']}")
    if c.get('present_requirements'):
        print(f"  Present: {c['present_requirements']}")
    if c.get('missing_requirements'):
        print(f"  Missing: {c['missing_requirements']}")

print("\n" + "=" * 60)
if errors:
    print(f"ERRORS: {errors}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
