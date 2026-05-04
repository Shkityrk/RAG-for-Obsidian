# Quality UI Test Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add focused backend tests and polish the primary React chat UI.

**Architecture:** Extract pure helpers from `backend/core/src/app.py` into `backend/core/src/core_utils.py`, keep the public API behavior unchanged, and test the extracted module directly.

**Tech Stack:** Python 3.12, pytest, FastAPI helper code, React 18, Vite, Mantine, Tabler icons.

---

### Task 1: Extract Core Helpers

**Files:**
- Create: `backend/core/src/core_utils.py`
- Modify: `backend/core/src/app.py`
- Test: `backend/core/tests/test_core_utils.py`

- [x] Move deterministic helpers into a dependency-light module.
- [x] Import those helpers from `app.py`.
- [x] Add pytest tests for the extracted behavior.

### Task 2: Polish Chat UI

**Files:**
- Modify: `client/ui/src/layouts/basic-layout/index.tsx`
- Modify: `client/ui/src/layouts/basic-layout/index.css`
- Modify: `client/ui/src/pages/chat/index.tsx`
- Modify: `client/ui/src/pages/chat/index.css`
- Modify: `client/ui/src/components/message/index.tsx`
- Modify: `client/ui/src/components/message/index.css`

- [x] Tighten navigation, chat panels, empty state, message readability, and source chips.
- [x] Keep controls icon-led and responsive.
- [x] Run TypeScript build and lint.

### Task 3: Review And Verify

**Files:**
- No new source files.

- [x] Run pytest for backend core helpers.
- [x] Run frontend build/lint where dependencies allow it.
- [x] Summarize architecture findings with file references and remaining risks.
