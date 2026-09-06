"""The product catalogue.

Separate module from dashboard.py so each router mounts under one prefix and
the URL layout stays visible in main.py.
"""

from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.config import db_list_tiers
from app.database.products import (
    db_create_product,
    db_get_product,
    db_list_price_lists,
    db_list_products,
    db_product_stock,
    db_update_product,
)
from app.logging.setup_logging import get_logger
from app.models.catalog import Product
from app.models.enums import UserRole
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal, require_roles
from app.schemas.dashboard import (
    ErrorResponse,
    ListProductsResponse,
    PricelistRow,
    ProductDetailData,
    ProductDetailResponse,
    ProductRow,
    ProductStockRow,
    SaveProductRequest,
)

logger = get_logger(__name__)
router = APIRouter()


def _price_rule(product: Product, adjustment_pct: float) -> str:
    """Describe a price list as a rule and the price it produces.

    Showing both means a rep can sanity-check the rule against the number
    rather than trusting one of them.
    """
    adjustment = Decimal(str(adjustment_pct))
    net = (
        Decimal(str(product.unit_price))
        * (Decimal("100") - adjustment)
        / Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if adjustment == 0:
        return f"List price, {net}"
    return f"List less {adjustment.normalize():f}%, {net}"


# Editing the catalogue is a configuration change, so it is gated the same way
# every other one is. Built here rather than imported from routes/admin.py -
# a route module is not a dependency library.
require_admin = require_roles({UserRole.ADMIN})


def _reject_negative_margin(payload) -> None:
    """A cost above the price would poison the margin indicator, the anomaly
    detector and the reports, all silently."""
    unit_price = Decimal(str(payload.unit_price))
    cost_price = Decimal(str(payload.cost_price))
    if cost_price > unit_price:
        raise _unprocessable(
            f"Cost price {cost_price} may not exceed the unit price {unit_price}"
        )


def _not_found(product_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ErrorResponse(
            success=False, error="Not Found", message=f"No product {product_id}"
        ).model_dump(),
    )


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=ErrorResponse(
            success=False, error="Unprocessable Entity", message=message
        ).model_dump(),
    )


def _load_product(db: Session, product_id: str) -> Product:
    """Resolve the "p<id>" form the catalogue exposes, or 404.

    Both the GET and the PUT go through here so they cannot disagree about what
    a product id looks like.
    """
    raw = product_id[1:] if product_id.startswith("p") else product_id
    product = db_get_product(db, int(raw)) if raw.isdigit() else None
    if product is None:
        raise _not_found(product_id)
    return product


@router.get(
    "",
    response_model=ListProductsResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_products(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> ListProductsResponse:
    rows = []
    for product in db_list_products(db):
        try:
            rows.append(
                ProductRow(
                    id=f"p{product.id}",
                    name=product.name,
                    category=product.category,
                    variants=0,
                    price=float(product.unit_price),
                    unit=product.unit,
                    tax=f"{float(product.tax_pct):g}%",
                    status="Active" if product.active else "Discontinued",
                )
            )
        except (TypeError, ValueError, AttributeError) as e:
            logger.warning("Skipping product %s: %s", product.id, e)

    return ListProductsResponse(
        success=True, message=f"Successfully retrieved {len(rows)} products", data=rows
    )


@router.get(
    "/{product_id}",
    response_model=ProductDetailResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def product_detail(
    product_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> ProductDetailResponse:
    product = _load_product(db, product_id)

    levels = db_product_stock(db, product.id)
    stock_rows = [
        ProductStockRow(
            warehouse=row.warehouse.name,
            region=row.warehouse.region,
            active=row.warehouse.active,
            on_hand=row.qty_on_hand,
            reserved=row.qty_reserved,
            available=row.available,
            reorder_point=row.reorder_point,
            reorder_qty=row.reorder_qty,
            needs_restock=row.reorder_point > 0 and row.available <= row.reorder_point,
        )
        for row in levels
    ]

    # Price rules per tier, derived from the tier ceilings rather than stored
    # twice - a tier's discount ceiling IS its price rule here.
    # Configured price lists win. They carry a currency and a real adjustment,
    # which the tier ceiling cannot express - a ceiling caps what a rep may give
    # away, a price list changes what the product costs that tier to begin with.
    configured = db_list_price_lists(db)
    if configured:
        pricelists = [
            PricelistRow(
                tier=tier.name,
                currency=row.currency,
                rule=_price_rule(product, row.adjustment_pct),
            )
            for row, tier in configured
        ]
    else:
        pricelists = [
            PricelistRow(
                tier=tier.name,
                currency="USD",
                rule=(
                    "Price, no adjustment"
                    if tier.max_discount_pct == 0
                    else f"Up to {float(tier.max_discount_pct):.0f}% off list"
                ),
            )
            for tier in db_list_tiers(db)
        ]

    return ProductDetailResponse(
        success=True,
        message="Product retrieved",
        data=ProductDetailData(
            id=f"p{product.id}",
            name=product.name,
            category=product.category,
            price=float(product.unit_price),
            cost_price=float(product.cost_price),
            unit=product.unit,
            # :g not :.0f - the edit screen parses this string back into the
            # PUT, so rounding it here would silently erase a fractional rate.
            tax=f"{float(product.tax_pct):g}%",
            description=product.description,
            subscription=product.is_subscription,
            cadence=product.recurring_cycle,
            qty_on_hand=product.qty_on_hand,
            variants=product.variants or [],
            pricelists=pricelists,
            stock=stock_rows,
            # What could actually be shipped today, ignoring depots the split
            # logic skips - the number a rep needs before promising a date.
            total_available=sum(
                row.available for row in levels if row.warehouse.active
            ),
        ),
    )


@router.put(
    "/{product_id}",
    response_model=ProductDetailResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 404, 422, 500)},
)
def save_product(
    product_id: str,
    payload: SaveProductRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> ProductDetailResponse:
    """Edit a product from Screen 17.

    Money crosses the wire as a number and is parsed straight to Decimal, so a
    price never passes through binary float on its way to a Numeric column.
    """
    product = _load_product(db, product_id)
    _reject_negative_margin(payload)

    unit_price = Decimal(str(payload.unit_price))
    cost_price = Decimal(str(payload.cost_price))

    db_update_product(
        db,
        product,
        name=payload.name,
        category=payload.category,
        unit_price=unit_price,
        cost_price=cost_price,
        unit=payload.unit,
        tax_pct=Decimal(str(payload.tax_pct)),
        description=payload.description,
        is_subscription=payload.is_subscription,
        recurring_cycle=payload.recurring_cycle,
    )
    db.commit()
    logger.info("%s saved product %s", user.email, product_id)

    return product_detail(product_id, db, user)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductDetailResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 422, 500)},
)
def create_product(
    payload: SaveProductRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> ProductDetailResponse:
    """Add a product to the catalogue.

    Same payload as the edit, because the fields a product has do not change
    between being created and being corrected. Stock is added per warehouse
    afterwards - a product exists before it sits anywhere.
    """
    _reject_negative_margin(payload)

    product = db_create_product(
        db,
        name=payload.name,
        category=payload.category,
        unit_price=Decimal(str(payload.unit_price)),
        cost_price=Decimal(str(payload.cost_price)),
        unit=payload.unit,
        tax_pct=Decimal(str(payload.tax_pct)),
        description=payload.description,
        is_subscription=payload.is_subscription,
        recurring_cycle=payload.recurring_cycle,
    )
    db.commit()
    logger.info("%s added product %s", user.email, product.name)
    return product_detail(f"p{product.id}", db, user)
