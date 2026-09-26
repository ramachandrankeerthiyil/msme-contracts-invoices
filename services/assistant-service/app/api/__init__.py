from app.api.chat import router as chat_router

# Each router is included with the service's API prefix (see app.main).
api_routers = [chat_router]
