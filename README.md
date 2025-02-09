# FastAI-API 
## A Seamless Drop-in Solution for OpenAI Tool Calling in FastAPI
---

## 📌 **Overview**
This project serves as a **drop-in replacement for FastAPI-based applications** or any API utilizing the OpenAPI format. It seamlessly integrates with an **already running FastAPI server**, enabling OpenAI-powered function calling, supporting:
- **Single API Mode** – Run a standalone FastAPI app with OpenAI-powered function calling.
- **Microservices Mode** – Run multiple services with an Nginx API gateway and OpenAPI-based function calling.
- **OpenAPI Integration** – Dynamically fetches OpenAPI specifications from services.
- **OpenAI API Calls** – Automates API interactions based on user instructions.

![Screen Recording 2025-02-06 at 8 26 27 AM](https://github.com/user-attachments/assets/7d0f5050-ac2b-42eb-a873-d62eca256c12)

---

## 🏗 **Project Structure**
```plaintext
fastapi_openapi/
│── src/                         # Source code
│   ├── services/                # Microservices
│   │   ├── user_service/        # User management API
│   │   ├── cart_service/        # Shopping cart API
│   ├── openapi/                 # OpenAPI specifications & processing
│   │   ├── specs/               # Raw OpenAPI spec files
│   │   ├── batch_openai_specs_save.py  # Fetch OpenAPI specs from services
│   ├── single_api_server.py      # Single API mode FastAPI server
│   ├── microservice_api_openai_calling.py  # Function calling in Microservices Mode
│   ├── single_api_openai_calling.py  # Function calling in Single API Mode
│── config/                       # Configuration files
│   ├── nginx/                    # Nginx configuration
│   ├── docker-compose.yml        # Docker configurations
│── .gitignore
│── README.md                     # Project description
│── requirements.txt               # Dependencies
```

---

## Usage Modes

### 1️⃣ Single API Mode (Standalone FastAPI Server)
Run a single FastAPI instance and interact with it via OpenAI function calling.

#### Step 1: Start the API Server
```sh
uvicorn src.single_api_server:app --reload
```
Runs the API on `http://127.0.0.1:8000/`.

#### Step 2: Run OpenAI Function Calling
```sh
python src/single_api_openai_calling.py
```
Uses OpenAI to interact with the API using natural language function calls.

---

### 2️⃣ Microservices Mode (Multiple APIs + API Gateway)
Run multiple FastAPI services behind an **Nginx API Gateway** and interact with them via OpenAI function calling.

#### Step 1: Start All Microservices
```sh
docker compose up --build
```
This will:
- Route API calls via **Nginx** at `localhost:8080/cart` and `localhost:8080/users`

#### Step 2: Fetch OpenAPI Specs of All Services
```sh
python3 src/openapi/batch_openai_specs_save.py
```
Saves OpenAPI specs of all running microservices in `src/openapi/openapi_specs`.

#### Step 3: Run Function Calling via OpenAI
```sh
python3 src/microservice_api_openai_calling.py
```
Uses OpenAI to generate and execute API calls dynamically.

#### Step 4: Replay the logs
```sh
python src/replay_logs.py
```

---

## API Endpoints
The project auto-generates API interactions using OpenAPI, but here are key endpoints:

### User Service (`/users`)
| Method | Endpoint        | Description       |
|--------|---------------|-------------------|
| `POST` | `/users/create` | Create a new user |
| `GET`  | `/users/{id}`   | Get user details  |

### Cart Service (`/cart`)
| Method | Endpoint        | Description       |
|--------|---------------|-------------------|
| `POST` | `/cart/{user_id}`     | Add item to cart |

---

## 📄 **License**
This project is licensed under the **MIT License**. See `LICENSE` for details.
