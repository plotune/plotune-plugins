---
type: llm
---

PASS if the reply says it will list the projects first, pick the project from the candidates, and ask the user when the choice is unclear instead of guessing a project_id.
FAIL if it invents a project id, claims it already ran tools and reports results, or says it will pick any project.
