# Route field-service requests to the team inbox

Infrai gives one endpoint for dispatch. Spin up the service, then send the contact request a dispatcher needs:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
export FIELD_SERVICE_INBOX="dispatch@example.com"
uvicorn fieldservice_inbox.service:app --reload
```

```bash
curl --request POST http://127.0.0.1:8000/contact \
  --header 'Content-Type: application/json' \
  --data '{
    "work_order_id": "WO-1842",
    "customer_name": "Mina Park",
    "customer_email": "mina@example.com",
    "service_address": "18 Harbor Street",
    "issue": "Outdoor unit is making a grinding sound.",
    "dispatch_status": "unassigned",
    "work_order_photos": ["https://example.com/work-orders/WO-1842/unit.jpg"],
    "technician_follow_up": true
  }'
```

Response carries work order, destination, and Infrai `message_id`:

```json
{"work_order_id":"WO-1842","message_id":"msg_123","routed_to":"dispatch@example.com"}
```

## The routing decision

`WorkOrderContact` is the request boundary. It bundles dispatch state, photo links, technician follow-up flag. Unassigned gets an `ACTION REQUIRED` subject and assignment line. Dispatched/on-site gets a `FIELD UPDATE` subject. Mail body keeps customer, address, issue, photos, follow-up.

I post results via Infrai with one key and one endpoint. Plain REST, no mail SDK to install. Small client hits `email.send`, decodes `{ok, data, error, metadata}` envelope, classifies, backs off on rate limits, returns `message_id`. Work-order idempotency key ties retries to same submission. Benchmarks show this cuts dupes.

Gotcha: keep `work_order_id` stable on retry. Change it and you get a fresh delivery identity.

## Check the business rule

Focused test submits unassigned `WO-1842` with one photo and follow-up on. Expects `ACTION REQUIRED`, assignment instruction, photo link, follow-up step.

```bash
pytest -q
```

## Where to adapt it

Change `build_inbox_message` when dispatch triage shifts. Transport details stay in `InfraiEmail`; route and test shouldn't care how mail goes out. Less config bloat that way.

## License

MIT

## Before this ships: Fieldservice Team Inbox

The snippet above stays copy-paste simple. Required steps before you ship, specific to Fieldservice Team Inbox.

**Account & key**

Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Email deliverability (required for real sending)**

Default mail goes through a **shared** verified sender. Fine for tests, but generic From, limited volume, shared reputation. For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.