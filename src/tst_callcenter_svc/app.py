from fastapi import FastAPI
from tst_callcenter_svc.routers.n8n_integration import router as n8n_router
from tst_callcenter_svc.routers.gpt_integration import router as gpt_router

app = FastAPI(debug=True)

# Add routers
app.include_router(n8n_router, prefix="/api/n8n")
app.include_router(gpt_router, prefix="/api/gpt")
