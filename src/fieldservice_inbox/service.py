from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .infrai_email import InfraiEmail, InfraiError
from .work_order_router import WorkOrderContact, build_inbox_message

app = FastAPI(title="Field-service inbox router")


class SubmissionAccepted(BaseModel):
    work_order_id: str
    message_id: str
    routed_to: str


@app.post("/contact", response_model=SubmissionAccepted, status_code=202)
def route_contact(contact: WorkOrderContact) -> SubmissionAccepted:
    api_key = os.environ.get("INFRAI_API_KEY")
    team_inbox = os.environ.get("FIELD_SERVICE_INBOX")
    if not api_key or not team_inbox:
        raise HTTPException(status_code=503, detail="service email is not configured")

    message = build_inbox_message(contact)
    try:
        message_id = InfraiEmail(api_key).send(
            to=team_inbox,
            subject=message.subject,
            text=message.text,
            idempotency_key=f"work-order-contact:{contact.work_order_id}",
        )
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": str(exc.detail.get("message", "request rejected"))},
        ) from exc
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail="email delivery request failed") from exc

    return SubmissionAccepted(
        work_order_id=contact.work_order_id,
        message_id=message_id,
        routed_to=team_inbox,
    )
