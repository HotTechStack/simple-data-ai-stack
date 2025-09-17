# Service Login and Connection Guide

## 1. NocoDB (http://localhost:8080)

### First Time Setup:
1. Open http://localhost:8080
2. You'll see the NocoDB setup wizard
3. Create your admin account:
   - **Email**: your-email@example.com
   - **Password**: YourStrongPassword123
4. Click "Let's Begin"

### Verify Database Connection:
1. After login, click "New Project"
2. Choose "Create By Connecting To An External Database"
3. Select "PostgreSQL"
4. Use these connection details:
   - **Host**: postgres
   - **Port**: 5432
   - **Username**: postgres
   - **Password**: SuperStrongPassword123
   - **Database**: root_db
5. Click "Test Connection" - should show green checkmark
6. Click "Submit" to create project

---

## 2. pgAdmin (http://localhost:8081)

### Login:
- **Email**: admin@yourdomain.com (from your .env file)
- **Password**: PgAdminPassword123 (from your .env file)

### Add PostgreSQL Server:
1. Right-click "Servers" in left panel
2. Select "Create" > "Server"
3. **General Tab**:
   - **Name**: PostgreSQL Main
4. **Connection Tab**:
   - **Host**: postgres
   - **Port**: 5432
   - **Database**: root_db
   - **Username**: postgres
   - **Password**: SuperStrongPassword123
5. Click "Save"

### Verify Connection:
- Expand "PostgreSQL Main" in left panel
- You should see "Databases" with "root_db"
- Click on "root_db" > "Schemas" > "public" > "Tables"
- You might see NocoDB tables if you created a project

---

## 3. pgbackweb (http://localhost:8085)

### First Time Setup:
1. Open http://localhost:8085
2. Create your admin account
3. Set up your first backup job

### Add Database Connection:
1. Go to "Databases" section
2. Click "Add Database"
3. Fill in:
   - **Name**: Main PostgreSQL
   - **Host**: postgres
   - **Port**: 5432
   - **Database**: root_db
   - **Username**: postgres
   - **Password**: SuperStrongPassword123
4. Click "Test Connection"
5. Save if test passes

### Create Backup Job:
1. Go to "Backups" section
2. Click "Create Backup"
3. Select your database
4. Configure schedule (e.g., daily at 2 AM)
5. Set retention policy

---

## 4. Uptime Kuma (http://localhost:3001)

### First Time Setup:
1. Open http://localhost:3001
2. Create admin account:
   - **Username**: admin
   - **Password**: YourMonitoringPassword123
   - **Confirm Password**: YourMonitoringPassword123
3. Click "Create"

### Add Monitoring for Your Services:
1. Click "Add New Monitor"
2. **Monitor NocoDB**:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: NocoDB
   - **URL**: http://nocodb:8080
   - **Heartbeat Interval**: 60 seconds
3. **Monitor pgAdmin**:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: pgAdmin
   - **URL**: http://pgadmin:80
4. **Monitor PostgreSQL**:
   - **Monitor Type**: Port
   - **Friendly Name**: PostgreSQL
   - **Hostname**: postgres
   - **Port**: 5432

---

## 5. Direct Database Connections

### PostgreSQL (localhost:5432)
Using any PostgreSQL client:
- **Host**: localhost
- **Port**: 5432
- **Database**: root_db
- **Username**: postgres
- **Password**: SuperStrongPassword123

### PgBouncer (localhost:6432)
Connection pooling layer:
- **Host**: localhost
- **Port**: 6432
- **Database**: root_db
- **Username**: postgres
- **Password**: SuperStrongPassword123

### Redis (localhost:6379)
Using redis-cli or any Redis client:
```bash
redis-cli -h localhost -p 6379 -a RedisPassword123
```

---

## 6. Quick Health Check Commands

### Check all containers are running:
```bash
docker compose ps
```

### Check logs for any service:
```bash
docker compose logs nocodb
docker compose logs postgres
docker compose logs pgadmin
docker compose logs pgbackweb
docker compose logs uptime-kuma
```

### Test PostgreSQL connection:
```bash
docker compose exec postgres psql -U postgres -d root_db -c "SELECT version();"
```

### Test Redis connection:
```bash
docker compose exec redis redis-cli -a RedisPassword123 ping
```

---

## 7. Troubleshooting Common Issues

### If NocoDB shows connection errors:
1. Check postgres container is healthy: `docker compose ps postgres`
2. Check logs: `docker compose logs postgres nocodb`
3. Verify environment variables in .env file

### If pgAdmin won't connect to PostgreSQL:
1. Use container name `postgres` not `localhost` for host
2. Ensure you're using the correct password from .env
3. Check if postgres container is accessible: `docker compose exec pgadmin ping postgres`

### If services can't reach each other:
1. All services should be on the same network
2. Use container names (postgres, redis, etc.) not localhost for inter-service communication
3. Check network: `docker network ls` and `docker network inspect <network_name>`