# Generated API client types

`schema.d.ts` in this folder is GENERATED from FastAPI's OpenAPI schema. Do not hand-edit it.

```bash
make gen-api        # python scripts/export_openapi.py  ->  docs/openapi.json
                    # npm run gen:api                   ->  src/lib/api/schema.d.ts
```

`src/lib/types.ts` re-exports the generated models, and `npm run typecheck` fails when the UI
and the API drift apart. Run `make gen-api` after any change to `apps/api/schemas` or a router.
