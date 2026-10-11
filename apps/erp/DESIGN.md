---
name: Northstar ERP Ledger
description: A local synthetic freight and invoice register for operational review.
colors:
  ground: "#f0f3ef"
  surface: "#ffffff"
  ink: "#1d2b27"
  muted: "#53635d"
  line: "#d3ddd7"
  harbor: "#215944"
  harbor-wash: "#e6f1ea"
  vermilion: "#963e2d"
  vermilion-wash: "#f8e9e5"
  amber: "#76500b"
  amber-wash: "#f6efdc"
typography:
  display:
    fontFamily: "Fira Sans, Segoe UI, sans-serif"
    fontSize: "clamp(27px, 3vw, 36px)"
    fontWeight: 600
    lineHeight: 1.12
    letterSpacing: "-0.04em"
  body:
    fontFamily: "Fira Sans, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Fira Mono, SFMono-Regular, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  square: "0px"
spacing:
  page-desktop: "24px"
  page-mobile: "12px"
components:
  button-refresh:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
    padding: "0 15px"
    height: "44px"
---

# Design System: Northstar ERP Ledger

## Overview

**Creative North Star: "The Freight Handoff Register"**

This local synthetic ERP presents invoices, customer accounts, and consumed ARG grants as one operational register. Its visual language is a cool mineral ground, crisp white ledger surfaces, fine rules, deep ink, and restrained harbor green for completed states. Vermilion and amber are reserved for exception and review states.

The page favors quick scanning and direct proof. Navigation links connect the invoice, account, and grant records; compact summaries orient the reviewer without displacing the ledger. Data is labeled as local and synthetic.

**Key Characteristics:**
- Flat, square-edged ledger surfaces with thin borders.
- Fira Sans for reading and Fira Mono for identifiers and measured values.
- State colors always accompany visible state labels.

## Colors

The palette pairs a cool green-gray field with ink and small state-coded accents.

### Primary
- **Harbor green** (`{colors.harbor}`): Completed states, identifiers, and focused navigation.

### Secondary
- **Signal vermilion** (`{colors.vermilion}`): Exceptions and visible keyboard focus.
- **Review amber** (`{colors.amber}`): Pending and review states.

### Neutral
- **Mineral ground** (`{colors.ground}`): Main page field.
- **Ledger white** (`{colors.surface}`): Header, tables, and controls.
- **Deep ink** (`{colors.ink}`): Primary text.
- **Muted ink** (`{colors.muted}`): Supporting text.
- **Fine rule** (`{colors.line}`): Table and section boundaries.

### Named Rules
**The Labeled State Rule.** Never rely on color alone to communicate a ledger state.

## Typography

**Display Font:** Fira Sans (with Segoe UI, sans-serif fallback)
**Body Font:** Fira Sans (with Segoe UI, sans-serif fallback)
**Label/Mono Font:** Fira Mono (with SFMono-Regular, Consolas, monospace fallback)

**Character:** Fira Sans keeps headings and operational copy clear at dense sizes. Fira Mono separates account codes, amounts, and system labels from prose.

### Hierarchy
- **Display** (600, `clamp(27px, 3vw, 36px)`, 1.12): Main page title.
- **Headline** (600, 20px, 1.25): Ledger section titles.
- **Title** (600, 15px, 1.5): Account names and brand title.
- **Body** (400, 15px, 1.5): Main reading copy.
- **Label** (400–650, 10–12px, up to `.07em` tracking): Table headings and system metadata.

## Layout

The desktop content is centered at a maximum width of 1320px with 24px side gutters; narrow viewports use 16px and then 12px gutters. A compact masthead and horizontal anchor navigation precede the title, proof strip, four-part register summary, and three ledger sections. At small widths the summary becomes a two-column grid. Wide data tables remain in labeled, keyboard-focusable horizontal scroll regions so all columns remain available.

## Elevation & Depth

The ledger is flat. Depth comes from white surfaces, thin boundary rules, and small tonal differences; the page uses no shadows.

## Shapes

Controls, labels, and table surfaces use square corners (`0px`). Thin borders establish grouping. State labels use compact rectangular fills with a one-pixel border.

## Components

### Buttons
- **Shape:** Square (`0px`).
- **Primary:** White refresh control with ink text and a 44px minimum height.
- **Hover / Focus:** Hover shifts the border and text to harbor green; keyboard focus uses a 3px vermilion outline with 3px offset.

### Chips
- **Style:** Compact rectangular status labels with tinted background and border.
- **State:** Harbor green for completed, amber for review, vermilion for exceptions, neutral gray-green otherwise; text repeats the state.

### Cards / Containers
- **Corner Style:** Square.
- **Background:** White on mineral ground.
- **Shadow Strategy:** None; thin rules provide structure.
- **Border:** One-pixel green-gray rules.
- **Internal Padding:** 12–18px for summary and table controls.

### Inputs / Fields
- **Style:** White field with one-pixel strong rule and square corners.
- **Focus:** Visible vermilion outline, 3px with offset.
- **Error / Disabled:** No custom error/disabled presentation is currently implemented.

### Navigation
- **Style:** Text links on white, aligned in one horizontal row. On narrow screens the row scrolls horizontally; each link keeps a readable touch height.

### Ledger Tables
Use compact uppercase column labels, restrained horizontal rules, tabular identifiers and amounts, and explicit empty states. On mobile, keep the table in a named, focusable horizontal scroll region.

## Do's and Don'ts

### Do:
- **Do** label the tenant as local and synthetic.
- **Do** use Fira Mono for identifiers and monetary values.
- **Do** preserve the invoice → customer → grant review sequence.
- **Do** retain keyboard focus and explicit labels on table scroll regions.

### Don't:
- **Don't** imply a synthetic record is a production ERP record.
- **Don't** communicate approval or execution state through color alone.
- **Don't** add decorative shadows, gradients, or fabricated paper textures.
