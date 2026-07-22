# AI Provider Configuration

The default provider is deterministic mock. It does not use network access, API keys, or paid AI services, and it is the only provider used by CI.

## Environment Variables

```text
SESAME_AI_PROVIDER=mock
SESAME_AI_BASE_URL=https://example.invalid/v1
SESAME_AI_API_KEY=replace-with-your-key
SESAME_AI_MODEL=replace-with-model-name
SESAME_AI_TIMEOUT_SECONDS=10
SESAME_AI_MAX_OUTPUT_CHARS=6000
```

Use `.env.example` as a template only. Do not commit `.env`.

## Providers

| Provider | Use | Network | CI | Status |
| --- | --- | --- | --- | --- |
| `mock` | deterministic tests, evals, offline development | no | yes | default |
| `openai-compatible` | optional real model integration | yes | no | opt-in only |

`OpenAICompatibleProvider` reads base URL, API key, model, timeout, and output budget from environment variables. It maps authentication, rate limit, network, timeout, and malformed response failures into provider errors without logging API keys or authorization headers.

If a real provider is not configured, the system keeps using mock. CI must not require secrets or call external AI services.

