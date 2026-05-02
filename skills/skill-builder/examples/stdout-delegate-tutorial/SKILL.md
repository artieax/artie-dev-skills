---
name: stdout-delegate-tutorial
description: Minimal 3-step chained example verifying the stdout-delegate pattern works end-to-end
version: 0.2.0
---

# stdout-delegate-tutorial

A 3-step chained Mode D demo. Each step emits one `__LLM_DELEGATE__` directive that writes
its result to a tmp file; the next step reads that file to build on the previous answer.

## Workflow

### Step 1 — pick a language

```bash
python3 tutorial.py --step 1
```

Emits:

```
__LLM_DELEGATE__: {"prompt": "Name one obscure programming language. Reply with the name only.", "out": "tmp/tutorial/lang.txt"}
```

Write the LLM response into `tmp/tutorial/lang.txt`.

---

### Step 2 — learn a fact

```bash
python3 tutorial.py --step 2
```

Reads `tmp/tutorial/lang.txt`, then emits:

```
__LLM_DELEGATE__: {"prompt": "Give one surprising fact about <lang> in one sentence.", "out": "tmp/tutorial/fact.txt"}
```

Write the LLM response into `tmp/tutorial/fact.txt`.

---

### Step 3 — get a verdict

```bash
python3 tutorial.py --step 3
```

Reads `tmp/tutorial/lang.txt` and `tmp/tutorial/fact.txt`, then emits:

```
__LLM_DELEGATE__: {"prompt": "Given this fact about <lang>: '<fact>' — should a beginner learn it? One sentence.", "out": "tmp/tutorial/verdict.txt"}
```

Write the LLM response into `tmp/tutorial/verdict.txt`.

---

### Step 4 — print the chain result

```bash
python3 tutorial.py --step 4
```

No directive — just prints the collected results:

```
=== Chain complete ===
Language : <lang>
Fact     : <fact>
Verdict  : <verdict>
```

If you see all three fields populated, the 3-step chain is working end-to-end.
