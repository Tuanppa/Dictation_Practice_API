# Dictation Practice API

Backend API cho ứng dụng học tiếng Anh Dictation Practice.

## 🚀 Features

- ✅ User Authentication (Email/Password)
- ✅ OAuth Support (Google, Apple)
- ✅ JWT Token-based Authentication
- ✅ User Management (CRUD)
- ✅ Premium Subscription Management
- ✅ Redis Caching
- ✅ PostgreSQL Database

## 📚 Tech Stack

- **Framework:** FastAPI 0.109.0
- **Database:** PostgreSQL
- **Cache:** Redis
- **Authentication:** JWT (python-jose)
- **Password Hashing:** Bcrypt/Passlib
- **ORM:** SQLAlchemy 2.0

## 🛠️ Local Development

### Requirements
- Python 3.11+
- PostgreSQL 15+
- Redis

### Setup

```bash
# Clone repository
git clone <your-repo>
cd Dictation_Practice_API

# Create virtual environment
conda create -n dictation_api python=3.11
conda activate dictation_api

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your configurations

# Create database
createdb dictation_practice_db

# Create tables
python create_tables.py

# Run server
uvicorn app.main:app --reload
```

Server will run at: http://localhost:8000

## 📖 API Documentation

Once the server is running:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 🔑 Environment Variables

```env
DATABASE_URL=postgresql://localhost/dictation_practice_db
REDIS_HOST=localhost
REDIS_PORT=6379
SECRET_KEY=your-secret-key-min-32-characters
ENVIRONMENT=development
```

## 🌐 Deployment (Railway)

Project is configured for Railway deployment:
- PostgreSQL plugin for database
- Redis plugin for caching
- Automatic migrations on deploy

## 📱 iOS App Integration

Base URL for production: `https://your-app.railway.app/api/v1`

Example Swift code:
```swift
let baseURL = "https://your-app.railway.app/api/v1"
```

## 👤 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/logout` - Logout
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

### Users
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update profile
- `PUT /api/v1/users/me/password` - Change password

### Admin
- `GET /api/v1/users` - List all users (admin only)
- `PUT /api/v1/users/{id}/premium` - Update premium status (admin only)

## 📄 License

MIT

## 👨‍💻 Author

Dictation Practice Team