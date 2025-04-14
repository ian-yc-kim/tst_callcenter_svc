from fastapi import FastAPI
from tst_callcenter_svc.routers.n8n_integration import router as n8n_router
from tst_callcenter_svc.routers.gpt_integration import router as gpt_router
from tst_callcenter_svc.routers.google_integration import router as google_router
from tst_callcenter_svc.routers.upload import router as upload_router
from tst_callcenter_svc.routers.result import router as result_router

app = FastAPI(debug=True)

# Add routers
app.include_router(n8n_router, prefix="/api/n8n")
app.include_router(gpt_router, prefix="/api/gpt")
app.include_router(google_router, prefix="/api/google")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(result_router, prefix="/api/v1")
