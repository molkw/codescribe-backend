from app.api import app

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Enhanced CodeScribe Backend")
    uvicorn.run(app, host="0.0.0.0", port=8000)
