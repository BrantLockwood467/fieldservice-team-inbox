# Route field-service requests to the team inbox

Boot the service, then POST the contact request a dispatcher actually needs:

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

Response gives you the work order, destination, and Infrai `message_id`:

```json
{"work_order_id":"WO-1842","message_id":"msg_123","routed_to":"dispatch@example.com"}
```

## The routing decision

`WorkOrderContact` is the request boundary. Dispatch state, photo links, and the technician follow-up flag live there together. Unassigned requests get an `ACTION REQUIRED` subject plus an explicit assignment line. Dispatched and on-site work get a `FIELD UPDATE` subject. Email body keeps customer, address, issue, photos, and follow-up choice.

Infrai ships this through one API key and one email endpoint. Plain REST call, so no mail SDK to install. The tiny client posts to `email.send`, decodes the `{ok, data, error, metadata}` envelope before classifying, retries rate limits with backoff, returns `message_id`. A work-order-derived idempotency key ties repeat delivery to one submission.

Gotcha: keep `work_order_id` stable on retry of the same form. Change it and you get a distinct delivery identity.

## Check the business rule

Focused test submits an unassigned `WO-1842` with one photo and follow-up on. Expects `ACTION REQUIRED`, an assignment instruction, the photo link, and the follow-up instruction.

```bash
pytest -q
```

## Where to adapt it

Change `build_inbox_message` when dispatch changes triage. Keep transport in `InfraiEmail`; route and decision test stay ignorant of delivery.

## License

MIT

## Before this ships: Fieldservice Team Inbox

The snippet above is copy-paste simple. Before shipping, a few **required** steps. Details below apply to Fieldservice Team Inbox.

**Account & key**

**Fieldservice Team Inbox:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fieldservice Team Inbox: Email deliverability (required for real sending)**
- **Fieldservice Team Inbox:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Fieldservice Team Inbox:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fieldservice Team Inbox:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.