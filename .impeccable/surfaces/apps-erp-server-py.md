---
version: 1
slug: "apps-erp-server-py"
primary_target: "apps/erp/server.py"
related_targets: []
---

# Northstar ERP: Ledger

## Surface

Standalone local ERP ledger at `apps/erp/server.py`, mode **Operate**. The visitor is a finance or customer operations reviewer scanning synthetic invoices, customer accounts, and consumed ARG grants. The job is to find a record and confirm its current target-system state. The page must distinguish ERP state from ARG approval and token evidence. No production ERP or data is implied.

## Direction contract

**THESIS:** Make each invoice read like a proof-carrying handoff: the record, its accounting state, and the ARG grant that reached it belong to one traceable workflow. Refuse the generic dark operations cockpit.

**OWN-WORLD:** A Northstar freight handoff register. Cool mineral-white grounds, deep ink, harbor green for completed states, and signal vermilion for exceptions. Use tight but readable ledger rows, stamped state labels, tabular numerals, a route-spine motif for section navigation, and restrained rules. No fake paper textures, glowing security decoration, or emoji icons.

**STORY:** The operator sees the invoice outcome, checks the customer account, then verifies the corresponding consumed grant. A pending ARG action remains visibly separate from an ERP mutation.

**FIRST VIEWPORT:** A compact system header and route-spine navigation sit above a plain-language “Invoice register” heading. A narrow register summary and labeled search occupy one row. The invoice table leads the page; customer accounts and grant receipts follow as anchored sections. Keep record codes, rupee amounts, statuses, and refund outcomes visible without horizontal overflow.

**FORM:** Proof-carrying freight handoff register, candidate 7 of 7 grounded forms, assigned by direction seed `76fe566a`. Raise from Ikeda: encode evidence with disciplined high-contrast rows, without strobing. Raise from Star Atlas: make magnitude and exception hierarchy legible with fixed labels and values. Raise from Crouwel: retain a visible alignment grid. Raise from Streaming Shelf: make row details keyboard discoverable. Raise from Transit Diagram: show workflow stages without losing adjacent context. Transit Diagram and monochrome claim-and-proof ledger remain competitive alternates; other dealt challengers were declined because they weaken either operator identification or ledger clarity.

**FINISH:** unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
