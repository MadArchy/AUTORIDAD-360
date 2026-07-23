# LinkedIn live (PUBLISH_NATIVE_LIVE)

## Modo seguro (default)

`PUBLISH_NATIVE_LIVE=false` → el adaptador hace **dry-run**: no llama a la API de LinkedIn.

## Requisitos para live

1. App LinkedIn Developer con producto **Share on LinkedIn** / UGC Posts
2. OAuth 2.0: scopes `w_member_social` (y los que exija el producto)
3. Obtener `access_token` de usuario + `external_account_id` (`urn:li:person:…` o member id)
4. En admin **Canales** → Connect cuenta LinkedIn (token cifrado en `channel_accounts.meta_json`)
5. `PUBLISH_NATIVE_LIVE=true` solo en el entorno que tenga tokens reales
6. Ejecutar `POST /publish/jobs/{id}/execute`

## Checklist pre-live

- [ ] Token no expirado
- [ ] `external_account_id` correcto
- [ ] Copy ≤ 3000 chars
- [ ] Job en estado programable / ready
- [ ] Dry-run OK primero con `PUBLISH_NATIVE_LIVE=false`
- [ ] Un job de prueba a cuenta real controlada

## Fallbacks

Sin token → modo asistido (copiar checklist).  
Meta/IG/YouTube/TikTok siguen stub/dry-run hasta OAuth de producción.
