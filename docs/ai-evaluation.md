# AI Evaluation

AI V0 evaluation data lives in:

```text
ai-controller/evals/ai_interaction_cases.json
```

Run it with:

```powershell
cd ai-controller
powershell -ExecutionPolicy Bypass -File .\run-cli.ps1 ai-eval --json
```

The eval runner uses `DeterministicMockProvider` and the real `AIInteractionLoop`. It does not call external AI APIs and does not use hardware.

## Coverage

- normal status queries
- normal simulator actions
- clarification prompts
- safety blocks
- adversarial inputs
- provider failures

Every case includes user input, initial simulator state, mock provider result, expected intent/action, confirmation expectation, execution expectation, hardware change expectation, and expected error code.

Current V0 intentionally supports a single action per turn. Oversized plans, recursive-style requests, and loop requests fail closed.
