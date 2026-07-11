from fastapi import FastAPI

app = FastAPI(title="EduLogicsAI Backend")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
