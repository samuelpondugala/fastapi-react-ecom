from fastapi import APIRouter

from app.api.v1.endpoints import (
    addresses,
    auth,
    cart,
    categories,
    coupons,
    health,
    orders,
    products,
    reviews,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(addresses.router, prefix="/addresses", tags=["addresses"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(cart.router, prefix="/cart", tags=["cart"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(coupons.router, prefix="/coupons", tags=["coupons"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
