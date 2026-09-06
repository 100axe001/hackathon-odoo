"""Backend administration: accounts, and the configuration screens."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.billing import db_list_plans
from app.database.config import (
    db_delete_category_ceiling,
    db_delete_plan,
    db_delete_tier,
    db_delete_warehouse,
    db_get_customer,
    db_get_upsell_rule,
    db_list_approval_rules,
    db_list_category_ceilings,
    db_list_customers,
    db_list_tiers,
    db_list_warehouses,
    db_replace_approval_rules,
    db_save_upsell_rule,
    db_upsert_category_ceiling,
    db_upsert_plan,
    db_upsert_tier,
    db_upsert_warehouse,
    db_warehouse_usage,
)
from app.database.users import db_create_user, db_email_exists
from app.logging.setup_logging import get_logger
from app.models.enums import RiskLevel, UserRole
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal, require_roles
from app.schemas.admin import (
    CategoryCeilingRow,
    ChainRow,
    CreateUserRequest,
    CreateUserResponse,
    CustomerOption,
    DiscountConfigData,
    DiscountConfigResponse,
    ErrorResponse,
    ListCustomersResponse,
    ListPlansResponse,
    ListWarehousesResponse,
    PlanRow,
    RoutingRule,
    SaveDiscountConfigRequest,
    SavePlansRequest,
    SaveRoutingRulesRequest,
    SaveUpsellRuleRequest,
    SaveWarehousesRequest,
    TierCeiling,
    UpsellRuleData,
    UpsellRuleResponse,
    UserData,
    WarehouseRow,
)
from app.utils.security import security_util_hash_password

logger = get_logger(__name__)
router = APIRouter()

# Account creation is an admin power. Self-signup deliberately cannot reach it -
# see the comment in routes/auth.py.
require_admin = require_roles({UserRole.ADMIN})

# PS section 3 gives "configures discount tiers and approval chains" to the
# Sales Manager, not only the admin. Warehouses, plans and products stay
# admin-only, which is where the same section puts backend setup.
require_config = require_roles({UserRole.ADMIN, UserRole.SALES_MANAGER})


def _conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ErrorResponse(
            success=False, error="Conflict", message=message
        ).model_dump(),
    )


def _bad_request(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ErrorResponse(
            success=False, error="Bad Request", message=message
        ).model_dump(),
    )


@router.get(
    "/customers",
    response_model=ListCustomersResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def list_customers(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> ListCustomersResponse:
    """Companies a portal account can be attached to, and a quotation raised for.

    Internal rather than admin-only: a rep picks the customer when creating a
    quotation, so restricting this to admins made creation impossible for the
    one role that does it most.
    """
    rows = [
        CustomerOption(id=c.id, name=c.name, tier=c.tier.name)
        for c in db_list_customers(db)
    ]
    return ListCustomersResponse(
        success=True, message=f"Successfully retrieved {len(rows)} customers", data=rows
    )


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateUserResponse,
    responses={code: {"model": ErrorResponse} for code in (400, 403, 409, 500)},
)
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> CreateUserResponse:
    """Create an account with a chosen role.

    This is the only path to a CUSTOMER account, and to any privileged internal
    role. Signup cannot reach it, so nobody can register themselves as the
    approver of their own discounts.
    """
    if db_email_exists(db, payload.email):
        raise _conflict("An account with that email already exists")

    if payload.role == UserRole.CUSTOMER:
        if payload.customer_id is None:
            raise _bad_request("A customer account must be linked to a customer")
        if db_get_customer(db, payload.customer_id) is None:
            raise _bad_request(f"No customer {payload.customer_id}")
    elif payload.customer_id is not None:
        raise _bad_request("Only a CUSTOMER account may be linked to a customer")

    created = db_create_user(
        db,
        email=payload.email,
        password_hash=security_util_hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        customer_id=payload.customer_id,
    )
    logger.info("%s created account %s (%s)", user.email, created.email, created.role)

    return CreateUserResponse(
        success=True,
        message="Account created",
        data=UserData(
            id=created.id,
            name=created.full_name,
            email=created.email,
            role=created.role,
        ),
    )


# ############################
# Discount configuration
# ############################


def _chain(db: Session) -> list[ChainRow]:
    """The editable form of the chain: roles per level, in acting order.

    MEDIUM and HIGH are always present even when a level has no rules, so the
    screen can show that a level currently auto-approves rather than hiding it.
    """
    by_level: dict[str, list[str]] = {}
    for rule in sorted(db_list_approval_rules(db), key=lambda r: r.step_order):
        by_level.setdefault(rule.level, []).append(rule.role)

    return [
        ChainRow(level=level, roles=by_level.get(level, []))
        for level in (RiskLevel.MEDIUM, RiskLevel.HIGH)
    ]


def _routing_rules(db: Session) -> list[RoutingRule]:
    """Screen 18's third table, built from the rules that actually route.

    Written out rather than stored as prose so the screen cannot drift from the
    behaviour - if an admin changes the chain, this text changes with it.
    """
    by_level: dict[str, list[str]] = {}
    for rule in db_list_approval_rules(db):
        by_level.setdefault(rule.level, []).append(rule.role.replace("_", " ").title())

    rows = [
        RoutingRule(
            range="Within tier and category limit",
            approval="No approval needed",
        )
    ]
    for level, roles in sorted(by_level.items()):
        rows.append(
            RoutingRule(
                range=f"Over limit, blended risk {level.lower()}",
                approval=" then ".join(roles),
            )
        )
    return rows


@router.get(
    "/discount-config",
    response_model=DiscountConfigResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def get_discount_config(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> DiscountConfigResponse:
    """The tables that drive the risk engine.

    Readable by any internal role: a rep needs to see the ceilings they are
    working against. Saving is admin-only.
    """
    return DiscountConfigResponse(
        success=True,
        message="Configuration retrieved",
        data=DiscountConfigData(
            tier_ceilings=[
                TierCeiling(tier=t.name, max_discount=float(t.max_discount_pct))
                for t in db_list_tiers(db)
            ],
            category_ceilings=[
                CategoryCeilingRow(
                    category=c.category, max_discount=float(c.max_discount_pct)
                )
                for c in db_list_category_ceilings(db)
            ],
            routing_rules=_routing_rules(db),
            chain=_chain(db),
        ),
    )


@router.put(
    "/discount-config",
    response_model=DiscountConfigResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def save_discount_config(
    payload: SaveDiscountConfigRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_config),
) -> DiscountConfigResponse:
    """Change the ceilings.

    These feed straight into the engine, so a saved change alters routing on the
    next submit. That is the point of Screen 18 - the rules live in data, not in
    code.
    """
    for row in payload.tier_ceilings:
        db_upsert_tier(db, row.tier, Decimal(str(row.max_discount)))
    for row in payload.category_ceilings:
        db_upsert_category_ceiling(db, row.category, Decimal(str(row.max_discount)))

    db.commit()
    logger.info("%s saved the discount configuration", user.email)
    return get_discount_config(db, user)


# ############################
# Warehouses
# ############################


@router.get(
    "/warehouses",
    response_model=ListWarehousesResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def list_warehouses(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> ListWarehousesResponse:
    usage = db_warehouse_usage(db)
    empty = {
        "product_lines": 0,
        "units_on_hand": 0,
        "units_reserved": 0,
        "units_available": 0,
        "below_reorder": 0,
        "fulfilled_lines": 0,
    }

    return ListWarehousesResponse(
        success=True,
        message="Warehouses retrieved",
        data=[
            WarehouseRow(
                id=w.id,
                name=w.name,
                region=w.region,
                shipping_cost_weight=float(w.shipping_cost_weight),
                active=w.active,
                **usage.get(w.id, empty),
            )
            for w in db_list_warehouses(db)
        ],
    )


@router.put(
    "/warehouses",
    response_model=ListWarehousesResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def save_warehouses(
    payload: SaveWarehousesRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> ListWarehousesResponse:
    """Warehouses and their shipping weighting, which the split objective uses."""
    for row in payload.warehouses:
        db_upsert_warehouse(
            db,
            name=row.name,
            region=row.region,
            shipping_cost_weight=Decimal(str(row.shipping_cost_weight)),
            active=row.active,
        )
    db.commit()
    logger.info("%s saved %d warehouses", user.email, len(payload.warehouses))
    return list_warehouses(db, user)


# ############################
# Subscription plans
# ############################


@router.get(
    "/subscription-plans",
    response_model=ListPlansResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def list_subscription_plans(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> ListPlansResponse:
    return ListPlansResponse(
        success=True,
        message="Plans retrieved",
        data=[
            PlanRow(
                id=p.id,
                name=p.name,
                cycle=p.cycle,
                price=float(p.price),
                proration_enabled=p.proration_enabled,
                refund_window_days=p.refund_window_days,
                cancellation_fee_pct=float(p.cancellation_fee_pct),
            )
            for p in db_list_plans(db)
        ],
    )


@router.put(
    "/subscription-plans",
    response_model=ListPlansResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def save_subscription_plans(
    payload: SavePlansRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> ListPlansResponse:
    for row in payload.plans:
        db_upsert_plan(
            db,
            name=row.name,
            cycle=row.cycle,
            price=Decimal(str(row.price)),
            proration_enabled=row.proration_enabled,
            refund_window_days=row.refund_window_days,
            cancellation_fee_pct=Decimal(str(row.cancellation_fee_pct)),
        )
    db.commit()
    logger.info("%s saved %d plans", user.email, len(payload.plans))
    return list_subscription_plans(db, user)


# ############################
# Approval chain
# ############################


@router.put(
    "/approval-rules",
    response_model=DiscountConfigResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 422, 500)},
)
def save_approval_rules(
    payload: SaveRoutingRulesRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_config),
) -> DiscountConfigResponse:
    """Rewrite which roles review which risk level.

    This is the other half of PS 4-A3: the ceilings decide a quotation's level,
    and these rules decide who then has to sign it off. Both are data, so the
    chain can change without a deploy.
    """
    if not payload.rules:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ErrorResponse(
                success=False,
                error="Unprocessable Entity",
                message="A chain with no steps would auto-approve every quotation",
            ).model_dump(),
        )

    db_replace_approval_rules(
        db, [(r.level, r.step_order, r.role) for r in payload.rules]
    )
    db.commit()
    logger.info("%s rewrote the approval chain", user.email)
    return get_discount_config(db, user)


# ############################
# Upsell rule
# ############################


@router.get(
    "/upsell-rule",
    response_model=UpsellRuleResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def get_upsell_rule(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> UpsellRuleResponse:
    rule = db_get_upsell_rule(db)
    db.commit()
    return UpsellRuleResponse(
        success=True,
        message="Upsell rule retrieved",
        data=UpsellRuleData(
            min_margin_pct=float(rule.min_margin_pct),
            max_suggestions=rule.max_suggestions,
        ),
    )


@router.put(
    "/upsell-rule",
    response_model=UpsellRuleResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def save_upsell_rule(
    payload: SaveUpsellRuleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> UpsellRuleResponse:
    """Raise the floor and thin-margin products stop being suggested."""
    db_save_upsell_rule(
        db,
        min_margin_pct=Decimal(str(payload.min_margin_pct)),
        max_suggestions=payload.max_suggestions,
    )
    db.commit()
    logger.info("%s set the upsell margin floor", user.email)
    return get_upsell_rule(db, user)


# ############################
# Removals
# ############################
#
# Each refuses with 409 and an explanation rather than cascading. Deleting a
# warehouse that has shipped, or a tier customers are on, would leave real
# records pointing at nothing - and a silent cascade is worse than a refusal
# that says what to do instead.


def _removed(message: str | None) -> None:
    if message:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorResponse(
                success=False, error="Conflict", message=message
            ).model_dump(),
        )


@router.delete(
    "/warehouses/{warehouse_id}",
    response_model=ListWarehousesResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 409, 500)},
)
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> ListWarehousesResponse:
    _removed(db_delete_warehouse(db, warehouse_id))
    db.commit()
    logger.info("%s deleted warehouse %s", user.email, warehouse_id)
    return list_warehouses(db, user)


@router.delete(
    "/subscription-plans/{plan_id}",
    response_model=ListPlansResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 409, 500)},
)
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> ListPlansResponse:
    _removed(db_delete_plan(db, plan_id))
    db.commit()
    logger.info("%s deleted plan %s", user.email, plan_id)
    return list_subscription_plans(db, user)


@router.delete(
    "/discount-tiers/{name}",
    response_model=DiscountConfigResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 409, 500)},
)
def delete_tier(
    name: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_config),
) -> DiscountConfigResponse:
    _removed(db_delete_tier(db, name))
    db.commit()
    logger.info("%s deleted tier %s", user.email, name)
    return get_discount_config(db, user)


@router.delete(
    "/category-ceilings/{category}",
    response_model=DiscountConfigResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 409, 500)},
)
def delete_category_ceiling(
    category: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_config),
) -> DiscountConfigResponse:
    _removed(db_delete_category_ceiling(db, category))
    db.commit()
    logger.info("%s deleted the %s ceiling", user.email, category)
    return get_discount_config(db, user)
