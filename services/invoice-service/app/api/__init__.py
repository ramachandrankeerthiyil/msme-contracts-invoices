from fastapi import APIRouter

from app.api import invoices, uploads

# Feature routers, each mounted under settings.api_prefix by create_app(). Mounting them with the
# prefix (rather than nesting them in one un-prefixed router) lets the list live at
# `/api/invoices` itself, without a trailing slash.
api_routers: list[APIRouter] = [uploads.router, invoices.router]
