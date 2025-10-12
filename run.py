"""
Script để chạy FastAPI server
Chạy: python run.py
"""
import sys
import os

# Thêm thư mục hiện tại vào Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 STARTING DICTATION PRACTICE API")
    print("=" * 60)
    print(f"📂 Working directory: {current_dir}")
    print(f"📍 Server URL: http://localhost:8000")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print(f"📖 ReDoc: http://localhost:8000/redoc")
    print(f"🔄 Auto-reload: Enabled")
    print(f"⚙️  Environment: Development")
    print("=" * 60)
    print("\n✨ Server is starting... Press CTRL+C to stop\n")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n\n❌ Error starting server: {e}")
        print("\n🔍 Troubleshooting tips:")
        print("  1. Check if port 8000 is already in use")
        print("  2. Ensure PostgreSQL is running: brew services start postgresql@15")
        print("  3. Ensure Redis is running: brew services start redis")
        print("  4. Check .env file exists and has correct configuration")