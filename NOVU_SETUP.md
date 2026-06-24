# Connecting Novu to Foresight

Foresight delivers its cart-recovery nudges through **[Novu](https://novu.co)** — an
open-source notification orchestrator. Foresight just *triggers a workflow*; Novu
fans it out to whatever provider you configure (WhatsApp, SMS, email, push, in-app).
Change how a nudge is delivered by editing the workflow in Novu — no code changes.

```
Foresight ──trigger event──▶ Novu workflow ──▶ provider (WhatsApp / SMS / email / push / in-app) ──▶ customer
```

## 1. Create the workflow in Novu
1. Sign in to Novu (cloud `dashboard.novu.co`, or your self-hosted instance).
2. **Workflows → Create**. Set the **trigger identifier** to `foresight-nudge`
   (or any name — just match it in Foresight's `NOVU_WORKFLOW_ID`).
3. Add a **channel step** for how you want to reach customers:
   - **Chat / WhatsApp**, **SMS**, **Email**, **Push**, or **In-App**.
   - Set the message body to the variable: `{{payload.body}}`
     (the full nudge text incl. the discount link is sent there).
   - Richer variables are also available if you want a custom template:
     `{{payload.name}}`, `{{payload.percent}}`, `{{payload.code}}`,
     `{{payload.link}}`, `{{payload.item}}`, `{{payload.value}}`.
4. **Connect a provider** for that channel (e.g. a WhatsApp Business / Twilio / email
   provider) under **Integrations**. Activate the workflow.

## 2. Connect Novu in Foresight
In the Foresight app → **Settings → Connections → Novu**, paste:
- **NOVU_API_KEY** — from Novu → *Settings → API Keys* (the secret key).
- **NOVU_WORKFLOW_ID** — `foresight-nudge` (or your trigger identifier).

Optional (env or settings):
- **NOVU_BASE_URL** — `https://api.novu.co` (US, default), `https://eu.api.novu.co` (EU),
  or your self-hosted API URL (e.g. `https://novu.yourdomain.com`).

Once `NOVU_API_KEY` is set, **all cart-recovery + manual nudges route through Novu**
automatically. Remove the key to fall back to the direct WhatsApp channel.

## 3. How Foresight triggers it
`POST {NOVU_BASE_URL}/v1/events/trigger` with `Authorization: ApiKey <key>`:
```json
{
  "name": "foresight-nudge",
  "to": { "subscriberId": "<customer id>", "phone": "+9162…" },
  "payload": { "body": "Hi Asha, you left … 10% off — code BACK10-7F3A …link",
               "name": "Asha", "percent": 10, "code": "BACK10-7F3A",
               "link": "https://…/r/abc", "item": "Sneakers", "value": 1499 }
}
```
Novu auto-creates the subscriber from `to`, runs the workflow, and delivers via your provider.

## Self-hosting (optional)
The Novu monorepo (api-service, worker, ws, dashboard) can be self-hosted via its
`docker/` compose files; then point `NOVU_BASE_URL` at your API host. The trigger
contract above is identical.
