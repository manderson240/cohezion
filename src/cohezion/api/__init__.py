from cohezion.api.research_endpoints import router as research_router

# ... existing code ...

# Register research endpoints
app.include_router(research_router, prefix="/api")
