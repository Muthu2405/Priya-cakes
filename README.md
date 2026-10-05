# Product Cost Calculator

Works out what a product costs to make from the ingredient quantities used.
React + Django REST Framework + MySQL.

- Ingredient price list per user (name, quantity, unit, price)
- Products: pick ingredients, enter the quantity used, add packaging, EB and labour costs, get the final cost; profit defaults to 30% of the cost (editable) and gives the selling price
- Units are converted automatically (kg/g, L/ml, pcs) and incompatible units are rejected
- Saved products keep the ingredient prices from the day they were saved
- Downloadable PDF costing report for every product
- Record sales (quantity, selling price, date) for products in your list or any other product typed in by name and get daily, weekly and monthly sales reports with revenue, cost and profit, per-product totals and CSV export. Weeks are plain 7-day blocks counted from the From date (e.g. 29 Sep – 5 Oct)
- Login required; each user only sees their own ingredients and products

## Run locally (Windows PowerShell)

**Backend**

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # then edit DB_PASSWORD (and DB_USER if not root)
```

Create the database once, in the MySQL shell or Workbench:

```sql
CREATE DATABASE cost_calculator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Frontend** (second terminal)

```powershell
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Sign in with the account you created. To add more users, open
http://127.0.0.1:8000/admin/ > Users > Add user. Each user gets their own separate data.

### Upgrading an existing install

```powershell
pip install -r requirements.txt
python manage.py migrate        # adds the sales table
python manage.py claim_orphans <your-username>
```

The migration removes "pieces made" and cost per piece. `claim_orphans` gives any
ingredients and products created before login existed to the user you name; until then
they are visible only in the admin.

## Tests

```powershell
cd backend;  $env:DB_ENGINE="sqlite"; python manage.py test      # 53 tests, no MySQL needed
cd frontend; npm test                                            # 22 tests
```

## Deploy free on Render + Neon

The root `Dockerfile` builds the React app and serves it together with the API from one
address, so there is no CORS setup. The database is Postgres through `DATABASE_URL`.

1. Push this project to a GitHub repository (the `.env` files are git-ignored).
2. **Neon** (neon.tech): create a free project, copy the connection string
   (`postgresql://...?sslmode=require`).
3. **Render** (render.com): New > Blueprint > pick the repository. It reads `render.yaml`.
   Fill in `DATABASE_URL` (Neon string), `DJANGO_SUPERUSER_USERNAME` and
   `DJANGO_SUPERUSER_PASSWORD` (your login), and set `BUSINESS_NAME`.
4. Wait for the build. Open the `https://<name>.onrender.com` address and sign in.
   Migrations and the admin user are created automatically on every start.

Free-tier limits: the Render service sleeps after about 15 minutes idle, so the first
visit takes up to a minute. Neon's free database keeps its data, but take your own
backups before relying on it for real records:
`pg_dump "$DATABASE_URL" > backup.sql`. For always-on hosting, use the Docker setup below.

## Deploy with Docker

Needs a server with Docker and a domain name.

1. Copy `.env.example` to `.env` and fill in every value.
2. `docker compose up -d --build`
3. `docker compose exec backend python manage.py createsuperuser`
4. Open the site. The app and API share one address, so no CORS setup is needed.

The compose file serves plain HTTP on port 80. Put HTTPS in front of it (a host-provided
certificate, Caddy, or a load balancer), then keep `DJANGO_SECURE_COOKIES=1`.

Back up the database with:
`docker compose exec db sh -c 'mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" cost_calculator' > backup.sql`

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login/` | Username and password in, token out |
| POST | `/api/auth/logout/` | Invalidate the token |
| GET | `/api/auth/me/` | Current user |
| GET/POST | `/api/ingredients/` | List (`?search=`, `?unit=`, `?active=`) or add |
| GET/PUT/DELETE | `/api/ingredients/<id>/` | One ingredient. Delete deactivates it if used in a product |
| GET/POST | `/api/products/` | List (`?search=`) or save |
| GET/PUT/DELETE | `/api/products/<id>/` | One product |
| POST | `/api/products/calculate/` | Preview a costing without saving |
| GET | `/api/products/<id>/pdf/` | PDF report |
| GET/POST | `/api/sales/` | List (`?product=`, `?from=`, `?to=`) or record a sale |
| GET/PUT/DELETE | `/api/sales/<id>/` | One sale |
| GET | `/api/sales/report/` | `?period=day\|week\|month&from=YYYY-MM-DD&to=YYYY-MM-DD` — totals, per-period series, per-product breakdown |
| GET | `/api/sales/report/csv/` | Same report as a CSV download |

Requests send `Authorization: Token <token>`.
