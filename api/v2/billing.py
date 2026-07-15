"""API v2 Billing router — tier gating, subscriptions, metering, and quota checks."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth.auth_middleware import get_current_user
from agents.license_agent import TIER_FEATURES, TIER_PRICING, generate_license
from db.connection import get_connection
from db import schema

router = APIRouter(prefix="/v2/billing", tags=["billing"])

TIER_QUOTAS = {
    "free": {"monthly_api_units": 1000},
    "pro": {"monthly_api_units": 50000},
    "enterprise": {"monthly_api_units": 500000},
}

STRIPE_API_BASE = "https://api.stripe.com/v1"


class CheckoutSessionCreate(BaseModel):
    tier: str = Field(..., pattern=r"^(pro|enterprise)$")
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class UsageEventCreate(BaseModel):
    endpoint: str = Field(..., min_length=1, max_length=255)
    units: int = Field(1, ge=1, le=10000)
    metadata: dict = Field(default_factory=dict)


class SubscriptionCancelRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class StripeSubscriptionEvent(BaseModel):
    stripe_session_id: str = Field(..., min_length=1, max_length=255)
    status: str = Field(..., pattern=r"^(pending|completed|refunded|failed)$")
    tier: str = Field("pro", pattern=r"^(pro|enterprise)$")
    amount_usd: float = Field(0.0, ge=0)


def _month_key(now: Optional[datetime] = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m")


def _resolve_user_email(cursor, current_user: dict) -> Optional[str]:
    if current_user.get("email"):
        return current_user.get("email")

    user_id = current_user.get("user_id")
    if not user_id:
        return None

    cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        return None
    if hasattr(row, "keys"):
        return row.get("email")
    try:
        return row["email"]
    except Exception:
        return None


def _effective_tier_rank(tier: str) -> int:
    return {"free": 0, "pro": 1, "enterprise": 2}.get(tier, 0)


def _get_effective_tier(cursor, current_user: dict) -> tuple[str, Optional[str]]:
    email = _resolve_user_email(cursor, current_user)
    if not email:
        return "free", None

    cursor.execute(
        """SELECT tier
           FROM user_licenses
           WHERE email = %s
             AND status = 'active'
             AND (expires_at IS NULL OR expires_at >= NOW())
           ORDER BY created_at DESC""",
        (email,),
    )
    rows = cursor.fetchall() or []

    tier = "free"
    for row in rows:
        row_tier = row.get("tier") if hasattr(row, "keys") else row["tier"]
        if _effective_tier_rank(row_tier) > _effective_tier_rank(tier):
            tier = row_tier

    return tier, email


def _calculate_monthly_usage(cursor, email: Optional[str], month_key: str) -> int:
    if not email:
        return 0

    cursor.execute(
        """SELECT COALESCE(SUM(units), 0) AS used
           FROM api_usage_events
           WHERE user_email = %s AND period_month = %s""",
        (email, month_key),
    )
    row = cursor.fetchone()
    if not row:
        return 0
    if hasattr(row, "keys"):
        return int(row.get("used", 0) or 0)
    try:
        return int(row["used"] or 0)
    except Exception:
        return 0


def _has_feature_access(tier: str, feature: str) -> bool:
    if tier == "enterprise":
        return True
    features = set(TIER_FEATURES.get("free", []))
    if tier in ("pro", "enterprise"):
        features.update(TIER_FEATURES.get("pro", []))
    if tier == "enterprise":
        features.update(TIER_FEATURES.get("enterprise", []))
    return feature in features


def _create_stripe_checkout_session(
    tier: str,
    email: Optional[str],
    success_url: str,
    cancel_url: str,
) -> Optional[dict]:
    """Create Stripe Checkout session if Stripe env config is present.

    Returns None when integration is not configured.
    Raises HTTPException for Stripe API failures.
    """
    secret_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    price_id = (
        os.environ.get("STRIPE_PRO_PRICE_ID", "").strip()
        if tier == "pro"
        else os.environ.get("STRIPE_ENTERPRISE_PRICE_ID", "").strip()
    )
    if not secret_key or not price_id:
        return None

    form_data = {
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "metadata[tier]": tier,
    }
    if email:
        form_data["customer_email"] = email

    body = urllib.parse.urlencode(form_data).encode("utf-8")
    req = urllib.request.Request(
        f"{STRIPE_API_BASE}/checkout/sessions",
        data=body,
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {secret_key}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return {
                "session_id": payload.get("id"),
                "checkout_url": payload.get("url"),
                "mode": payload.get("mode", "subscription"),
                "provider": "stripe",
            }
    except urllib.error.HTTPError as e:
        detail = "Stripe checkout session creation failed"
        try:
            body_text = e.read().decode("utf-8")
            stripe_payload = json.loads(body_text)
            detail = stripe_payload.get("error", {}).get("message", detail)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stripe request failed: {e}")


@router.get("/tier")
def get_tier(current_user: dict = Depends(get_current_user)):
    """Return effective tier + entitlements for the current user."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    tier, email = _get_effective_tier(cursor, current_user)

    cursor.close()
    conn.close()

    return {
        "tier": tier,
        "email": email,
        "features": TIER_FEATURES.get(tier, []),
        "quota": TIER_QUOTAS.get(tier, {}),
    }


@router.get("/entitlements")
def get_entitlements(current_user: dict = Depends(get_current_user)):
    """Return plan entitlements with pricing metadata."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    tier, _ = _get_effective_tier(cursor, current_user)

    cursor.close()
    conn.close()

    return {
        "tier": tier,
        "entitlements": {
            "features": TIER_FEATURES.get(tier, []),
            "pricing": TIER_PRICING.get(tier, {}),
            "quota": TIER_QUOTAS.get(tier, {}),
        },
    }


@router.get("/check-feature")
def check_feature_access(
    feature: str = Query(..., min_length=1),
    current_user: dict = Depends(get_current_user),
):
    """Check whether current user tier can access a named feature."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    tier, _ = _get_effective_tier(cursor, current_user)
    allowed = _has_feature_access(tier, feature)

    cursor.close()
    conn.close()

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Feature '{feature}' requires a higher tier",
        )

    return {"tier": tier, "feature": feature, "allowed": True}


@router.get("/subscription")
def get_subscription(current_user: dict = Depends(get_current_user)):
    """Get subscription and payment summary for the authenticated user."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    tier, email = _get_effective_tier(cursor, current_user)

    active_license = None
    if email:
        cursor.execute(
            """SELECT license_key, tier, status, expires_at, stripe_session_id, created_at
               FROM user_licenses
               WHERE email = %s
               ORDER BY created_at DESC
               LIMIT 1""",
            (email,),
        )
        row = cursor.fetchone()
        if row:
            active_license = dict(row) if hasattr(row, "keys") else None

    payment = None
    if email:
        cursor.execute(
            """SELECT stripe_session_id, tier, amount_usd, status, created_at
               FROM payment_events
               WHERE customer_email = %s
               ORDER BY created_at DESC
               LIMIT 1""",
            (email,),
        )
        row = cursor.fetchone()
        if row:
            payment = dict(row) if hasattr(row, "keys") else None

    cursor.close()
    conn.close()

    return {
        "tier": tier,
        "email": email,
        "license": active_license,
        "latest_payment": payment,
    }


@router.post("/subscription/cancel")
def cancel_subscription(
    body: SubscriptionCancelRequest,
    current_user: dict = Depends(get_current_user),
):
    """Cancel current user's active paid subscription and revoke licenses."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    _, email = _get_effective_tier(cursor, current_user)
    if not email:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User email not found")

    cursor.execute(
        """UPDATE user_licenses
           SET status = 'revoked'
           WHERE email = %s AND status = 'active' AND tier IN ('pro', 'enterprise')""",
        (email,),
    )
    revoked = cursor.rowcount

    cursor.execute(
        """INSERT INTO payment_events
           (stripe_session_id, customer_email, tier, amount_usd, status)
           VALUES (%s, %s, %s, %s, %s)""",
        (
            f"manual_cancel_{current_user.get('user_id')}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            email,
            "pro",
            0,
            "refunded",
        ),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "email": email,
        "revoked_licenses": revoked,
        "status": "canceled",
        "reason": body.reason,
    }


@router.post("/subscription/events/stripe")
def ingest_stripe_subscription_event(
    body: StripeSubscriptionEvent,
    current_user: dict = Depends(get_current_user),
):
    """Ingest a Stripe subscription event and sync payment/license state."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    _, email = _get_effective_tier(cursor, current_user)
    if not email:
        email = current_user.get("email")

    cursor.execute(
        "SELECT id FROM payment_events WHERE stripe_session_id = %s",
        (body.stripe_session_id,),
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            """UPDATE payment_events
               SET customer_email = %s, tier = %s, amount_usd = %s, status = %s
               WHERE stripe_session_id = %s""",
            (
                email,
                body.tier,
                body.amount_usd,
                body.status,
                body.stripe_session_id,
            ),
        )
    else:
        cursor.execute(
            """INSERT INTO payment_events
               (stripe_session_id, customer_email, tier, amount_usd, status)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                body.stripe_session_id,
                email,
                body.tier,
                body.amount_usd,
                body.status,
            ),
        )

    license_key = None
    if body.status == "completed":
        license_key = generate_license(body.tier, 365)
        cursor.execute(
            """UPDATE user_licenses
               SET email = %s, stripe_session_id = %s, status = 'active'
               WHERE license_key = %s""",
            (email, body.stripe_session_id, license_key),
        )

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "stripe_session_id": body.stripe_session_id,
        "status": body.status,
        "tier": body.tier,
        "email": email,
        "license_key": license_key,
    }


@router.post("/checkout-session")
def create_checkout_session(
    body: CheckoutSessionCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a checkout-session payload for Stripe frontends."""
    tier = body.tier.lower()
    if tier not in ("pro", "enterprise"):
        raise HTTPException(status_code=400, detail="Only paid tiers are eligible")

    success_url = body.success_url or "https://example.com/success"
    cancel_url = body.cancel_url or "https://example.com/cancel"
    stripe_session = _create_stripe_checkout_session(
        tier=tier,
        email=current_user.get("email"),
        success_url=success_url,
        cancel_url=cancel_url,
    )

    if stripe_session:
        return {
            **stripe_session,
            "tier": tier,
            "price": TIER_PRICING[tier],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "user": {
                "user_id": current_user.get("user_id"),
                "email": current_user.get("email"),
            },
        }

    # Fallback for local/dev when Stripe credentials are not configured.
    pro_url = os.environ.get("STRIPE_PRO_URL", "")
    enterprise_url = os.environ.get("STRIPE_ENTERPRISE_URL", "")
    checkout_url = pro_url if tier == "pro" else enterprise_url
    if not checkout_url:
        checkout_url = f"https://example.com/checkout/{tier}"

    return {
        "checkout_url": checkout_url,
        "session_id": None,
        "provider": "fallback",
        "tier": tier,
        "price": TIER_PRICING[tier],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "user": {
            "user_id": current_user.get("user_id"),
            "email": current_user.get("email"),
        },
    }


@router.post("/usage/events")
def record_usage_event(
    body: UsageEventCreate,
    current_user: dict = Depends(get_current_user),
):
    """Record API usage and enforce monthly quota by tier."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    tier, email = _get_effective_tier(cursor, current_user)
    month = _month_key()

    used = _calculate_monthly_usage(cursor, email, month)
    quota = TIER_QUOTAS.get(tier, TIER_QUOTAS["free"])["monthly_api_units"]
    if used + body.units > quota:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=429,
            detail=(
                f"Monthly quota exceeded for tier '{tier}'. "
                f"used={used}, requested={body.units}, quota={quota}"
            ),
        )

    cursor.execute(
        """INSERT INTO api_usage_events
           (user_id, user_email, tier, endpoint, units, metadata_json, period_month)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (
            current_user.get("user_id"),
            email,
            tier,
            body.endpoint,
            body.units,
            json.dumps(body.metadata),
            month,
        ),
    )
    event_id = cursor.lastrowid
    conn.commit()

    cursor.close()
    conn.close()

    return {
        "event_id": event_id,
        "tier": tier,
        "month": month,
        "used": used + body.units,
        "quota": quota,
        "remaining": max(0, quota - (used + body.units)),
    }


@router.get("/usage/summary")
def usage_summary(
    month: Optional[str] = Query(None, description="Month key format: YYYY-MM"),
    current_user: dict = Depends(get_current_user),
):
    """Get per-endpoint usage totals for the current month."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    tier, email = _get_effective_tier(cursor, current_user)
    month_key = month or _month_key()

    if not email:
        cursor.close()
        conn.close()
        return {"tier": tier, "month": month_key, "usage": []}

    cursor.execute(
        """SELECT endpoint, SUM(units) AS units
           FROM api_usage_events
           WHERE user_email = %s AND period_month = %s
           GROUP BY endpoint
           ORDER BY units DESC""",
        (email, month_key),
    )
    rows = [dict(r) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return {
        "tier": tier,
        "month": month_key,
        "usage": rows,
    }


@router.get("/quota")
def get_quota(current_user: dict = Depends(get_current_user)):
    """Return quota utilization for the current user and month."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    tier, email = _get_effective_tier(cursor, current_user)
    month = _month_key()
    used = _calculate_monthly_usage(cursor, email, month)
    quota = TIER_QUOTAS.get(tier, TIER_QUOTAS["free"])["monthly_api_units"]

    cursor.close()
    conn.close()

    return {
        "tier": tier,
        "month": month,
        "used": used,
        "quota": quota,
        "remaining": max(0, quota - used),
        "percent_used": round((used / quota) * 100, 2) if quota else 0,
    }
