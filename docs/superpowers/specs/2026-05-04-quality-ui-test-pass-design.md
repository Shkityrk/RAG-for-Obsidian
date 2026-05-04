# Quality UI Test Pass Design

**Goal:** stabilize the project with focused backend unit tests, a cleaner chat UI, and a grounded architecture review.

**Architecture:** keep the running service boundaries intact. Extract only pure `core` helpers that can be tested without Postgres, MinIO, or Qdrant, then leave the larger `core/src/app.py` split as a follow-up architecture recommendation.

**Frontend:** keep Mantine and Tabler icons. Refine the app shell and chat workspace into a quieter product UI with compact sidebars, clear empty states, stable sizing, and readable message surfaces.

**Testing:** add pytest coverage for deterministic text splitting, vault id compatibility, JSON extraction from LLM output, chat title derivation, and JWT username extraction.
