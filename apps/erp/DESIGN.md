# Design System: Northstar Freight Core Ledger

## Overview
**Creative North Star: "Industrial Operational Freight Ledger"**

Northstar Freight Core is an authoritative enterprise ledger for accounts receivable, freight manifests, and cryptographic ARG settlement receipts.

## Key Principles & Anti-Slop Decisions
1. **Zero Generic AI Blue**: Eliminated all saturated blues (`#2563eb`, `#3b82f6`, `#0078d4`) and cookie-cutter SaaS styling.
2. **Replaced Repetitive KPI Cards**: Replaced the typical 4-box card grid with a unified **Operational Manifest Strip** displaying freight volume, settlement figures, and proof token counts.
3. **Master-Detail Two-Panel Workstation**:
   - Left: High-density Accounts Receivable ledger, customer directory, and cryptographic grant receipt vault.
   - Right: Interactive **Cryptographic Settlement Inspector** detailing HMAC-SHA256 verification, replay resistance, and operator authorization.
4. **Palette**:
   - Masthead: Charcoal iron `#14171a` with amber gold accent `#d99b26`
   - Ledger Sheet: Warm technical parchment `#f6f5f0` and pure surface `#ffffff`
   - Rules: Precision hairline `#d4d2c9`
   - Settled & Verified: Forest Spruce `#194433`, wash `#e8f3ed`
   - Exceptions & Refunds: Madder Rust `#872b1e`, wash `#fcedea`
   - Review & Staged: Vintage Brass `#785312`, wash `#faf3e4`
5. **Real-time Synchronization**: Background polling every 3 seconds to reflect live updates upon ARG approval.
