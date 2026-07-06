# Online Bookstore

## Stack

- Frontend: React + Vite + Redux Toolkit + Tailwind CSS
- Backend: FastAPI + SQLAlchemy + MySQL
- Auth: JWT
- Migrations: Alembic-ready

## Structure

```text
backend/
  .env
  .env.example
  app/
  requirements.txt
  server/
n8n/
  N8N_ASSISTANT_INTEGRATION.md
frontend/
  index.html
  package.json
  package-lock.json
  postcss.config.js
  tailwind.config.js
  vite.config.js
  src/
  dist/
  node_modules/
```

## Setup

### Database

Run:

```bash
mysql -u root -p < backend/server/schema.sql
```

### Backend

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 4001 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment

Copy `backend/.env.example` to `backend/.env` and update values.

Required backend keys:

- `DATABASE_URL`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

Assistant-related keys:

- `N8N_CHAT_WEBHOOK_URL`
- `ASSISTANT_TEMPERATURE`

The repository default is `ASSISTANT_TEMPERATURE=0.5`. This repo exposes that value in backend settings and environment files. If your n8n workflow or model node supports a temperature field, set that node to `0.5` too so the external assistant behavior matches this project configuration.

When `N8N_CHAT_WEBHOOK_URL` is configured, the backend assistant will send a JSON payload to that webhook for informational assistant replies. The payload includes:

- `chatInput`
- `sessionId`
- `temperature`
- `intentHint`
- `state`
- `timestamp`
- `user`
- `selectedBook`

The backend expects a JSON response with a reply in one of these fields:

- `reply`
- `message`
- `output`

See `n8n/N8N_ASSISTANT_INTEGRATION.md` for a concrete request/response contract and a ready-to-copy n8n Code node example.

## API

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /categories`
- `GET /books`
- `GET /books/{id}`
- `POST /books`
- `PUT /books/{id}`
- `DELETE /books/{id}`
- `GET /cart`
- `POST /cart/add`
- `PUT /cart/update`
- `DELETE /cart/remove/{book_id}`
- `DELETE /cart/clear`
- `POST /orders/checkout`
- `GET /orders/my`
- `GET /orders/{id}`
- `GET /admin/orders`
- `PUT /admin/orders/{id}/status`
- `POST /reviews`
- `PUT /reviews/{id}`
- `DELETE /reviews/{id}`
- `GET /reviews/book/{book_id}`
- `GET /wishlist`
- `POST /wishlist/add`
- `DELETE /wishlist/remove/{book_id}`
- `GET /admin/stats`
