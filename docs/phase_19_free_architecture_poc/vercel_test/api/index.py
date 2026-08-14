from fastapi import FastAPI

app = FastAPI(title="Vercel POC")

@app.get("/api/health")
def health():
    return {"status": "ok"}
