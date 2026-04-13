# KISS First-Principles — Function-Level Survival Test

**Owner:** Allan
**Scope:** Every function, component, and file in any project
**Method:** Each function must prove it is irreducible, not absorbable, and justified by a requirement

---

## Survival test — 4 questions per function

1. **Is this truly irreducible?** Or is it a thin wrapper around one call?
2. **Can another existing function absorb this?** If merging two functions makes them simpler and loses nothing, merge.
3. **Is this a function or a config lookup?** If the entire body is reading a value and returning it, it's config — move it there.
4. **Does this exist because of real complexity, or because an agent over-engineered it?** If the answer is "it was generated and nobody questioned it," it fails.

If any answer is "no / yes / delete," the code is wrong. Reviewers enforce.

---

## Coding rules

1. **No hardcoding** — Every configurable value goes to a file. Config in `.json`, prompts in `.md`.
   **Why:** Maintainability. Allan iterates on configuration separately from code.

2. **Don't carry over dead features** — Features must match the actual workflow, not be inherited from old architecture.
   **Why:** Every feature that's "just there from before" is tech debt that slows everything down.
   **How to apply:** Before implementing any feature, ask "is this in the spec? does it serve a current requirement?"

3. **Define contracts first** — Interfaces before code.
   **Why:** Prevents refactoring halfway through. "If not I know what happens."

4. **KISS over completeness** — Build what's needed now. Spec holds future extensions.
   **Why:** "Things are evolving so fast you can't predict anything." Speculative code rots.
   **How to apply:** If you're building something not in the current sprint scope, stop and check.

5. **Surgical edits only** — Don't rewrite files. Change what needs changing, leave the rest.
   **Why:** Large rewrites introduce regressions and make diffs unreadable for reviewers.

6. **No new abstractions without a requirement** — No new classes, modules, or wrapper layers unless the spec explicitly calls for them.
   **Why:** Abstractions are the #1 source of agent over-engineering. Three similar lines are better than a premature abstraction.
