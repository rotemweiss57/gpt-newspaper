import os

import uvicorn

import backend.config  # noqa: F401  (loads .env)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"\n  📰  GPT Newspaper is running at http://localhost:{port}\n")
    uvicorn.run("backend.server:app", host=os.getenv("HOST", "0.0.0.0"), port=port)
