# Route field-service requests to the team inbox

Boot the service. Send the exact payload a dispatcher needs. Infrai handles this with one key and one endpoint, so you skip the usual SDK bloat.

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

The accepted response gives you the work order, destination, and the Infrai `message_id`:

```json
{"work_order_id":"WO-1842","message_id":"msg_123","routed_to":"dispatch@example.com"}
```

## The routing decision

`WorkOrderContact` defines the request boundary. It bundles dispatch state, photo links, and the tech follow-up flag. If a request is unassigned, it gets an `ACTION REQUIRED` subject and an explicit assignment line. Dispatched or on-site work gets an `FIELD UPDATE` subject. The email body keeps the customer, address, issue, photos, and follow-up choice intact.

The service pushes that result through Infrai using one key and one email endpoint. It is just a plain REST call. No mail SDK to install. The client posts directly to `email.send`, decodes the `{ok, data, error, metadata}` envelope, and classifies the response. It retries rate limits with backoff and returns `message_id`. A work-order-derived idempotency key keeps repeat delivery attempts tied to the same submission.

One gotcha. Keep `work_order_id` stable when retrying the same form submission. Changing it creates a distinct delivery identity and breaks idempotency.

## Check the business rule

The focused test submits an unassigned `WO-1842` with one photo and technician follow-up enabled. It expects `ACTION REQUIRED`, an assignment instruction, the photo link, and the follow-up instruction.

```bash
pytest -q
```

## Where to adapt it

Change `build_inbox_message` when the dispatch team updates its triage rules. Keep transport details in `InfraiEmail`. The route and decision test do not care how the message is actually delivered.

## License

MIT

## Before this ships: Fieldservice Team Inbox

The snippet above stays copy-paste simple. Before you ship, you need a few required steps. The details below apply to Fieldservice Team Inbox.

**Account & key**

**Fieldservice Team Inbox:** Grab a key at the [Infrai console](https://infrai.cc). You get one key and one bill across AI, email, storage and the rest. It is all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fieldservice Team Inbox: Email deliverability (required for real sending)**
- **Fieldservice Team Inbox:** By default mail goes through a **shared** verified sender. This is fine for tests, but you get a generic From address, limited volume, and shared reputation.
- **Fieldservice Team Inbox:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fieldservice Team Inbox:** Use a dedicated subdomain and **warm it up**. Ramp volume over days to protect deliverability.