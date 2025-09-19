# Simple Data Stack with PostgreSQL & NocoDB

A complete data stack built with Docker Compose featuring PostgreSQL database, NocoDB no-code interface, automated backups, connection pooling, and monitoring.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Business      │    │   Developers     │    │   DevOps        │
│   Users         │    │                  │    │   Team          │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │ NocoDB                │ pgAdmin               │ Uptime Kuma
         │ (Port 8080)           │ (Port 8081)           │ (Port 3001)
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      PostgreSQL         │
                    │     (Port 5432)         │
                    │   ┌─────────────────┐   │
                    │   │   PgBouncer     │   │
                    │   │  (Port 6432)    │   │
                    │   └─────────────────┘   │
                    └─────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │       Redis             │
                    │    (Port 6379)          │
                    └─────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    pgbackweb            │
                    │    (Port 8085)          │
                    └─────────────────────────┘
```

## Services Included

| Service | Port | Purpose | User Type |
|---------|------|---------|-----------|
| **NocoDB** | 8080 | No-code database interface | Business Users |
| **pgAdmin** | 8081 | Database administration | Developers |
| **pgbackweb** | 8085 | Backup management | DevOps |
| **Uptime Kuma** | 3001 | Service monitoring | All Teams |
| **PostgreSQL** | 5432 | Main database | Backend |
| **PgBouncer** | 6432 | Connection pooling | Backend |
| **Redis** | 6379 | Caching layer | Backend |

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- 4GB+ RAM available
- Ports 8080, 8081, 8085, 3001, 5432, 6379, 6432 available

### 2. Setup

```bash
# Clone or create project directory
mkdir data-stack && cd data-stack

# Create required directories
mkdir -p init-scripts backups

# Create .env file (see Environment Variables section below)
```

### 3. Environment Variables

Create a `.env` file with these values:

```env
# PostgreSQL - Using NocoDB defaults
POSTGRES_DB=root_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=SuperStrongPassword123

# Redis
REDIS_PASSWORD=RedisPassword123

# pgAdmin
PGADMIN_EMAIL=admin@yourdomain.com
PGADMIN_PASSWORD=PgAdminPassword123

# pgbackweb
PBW_ENCRYPTION_KEY=your-32-character-encryption-key-12
```

### 4. Deploy

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## Service Configuration

### NocoDB Setup (http://localhost:8080)

**First Time Setup:**
1. Open http://localhost:8080
2. Create admin account with your preferred credentials
3. Click "Let's Begin"

**Connect to PostgreSQL:**
1. Create New Project → "Connect External Database"
2. Select PostgreSQL and enter:
   - Host: `postgres`
   - Port: `5432`
   - Username: `postgres`
   - Password: `SuperStrongPassword123`
   - Database: `root_db`
3. Test connection and save

**User Management:**
1. Go to Team & Settings
2. Invite users with appropriate roles:
   - **Creator**: Full database access
   - **Editor**: Can edit data
   - **Viewer**: Read-only access
   - **Commenter**: Can only comment

### pgAdmin Setup (http://localhost:8081)

**Login:**
- Email: `admin@yourdomain.com`
- Password: `PgAdminPassword123`

**Add PostgreSQL Server:**
1. Right-click Servers → Create → Server
2. General Tab: Name = "PostgreSQL Main"
3. Connection Tab:
   - Host: `postgres`
   - Port: `5432`
   - Database: `root_db`
   - Username: `postgres`
   - Password: `SuperStrongPassword123`

### pgbackweb Setup (http://localhost:8085)

**Initial Configuration:**
1. Create admin account
2. Add Database Connection:
   - Name: "Main PostgreSQL"
   - Host: `postgres`
   - Port: `5432`
   - Database: `root_db`
   - Username: `postgres`
   - Password: `SuperStrongPassword123`

**Create Backup Job:**
1. Go to Backups → Create Backup
2. Select database and set schedule
3. Configure retention policy (e.g., keep 7 daily, 4 weekly)
4. Test backup job

### Uptime Kuma Setup (http://localhost:3001)

**Setup Monitoring:**
1. Create admin account
2. Add monitors for each service:

| Service | Type | URL/Host | Port |
|---------|------|----------|------|
| NocoDB | HTTP(s) | http://nocodb:8080 | - |
| pgAdmin | HTTP(s) | http://pgadmin:80 | - |
| PostgreSQL | Port | postgres | 5432 |
| Redis | Port | redis | 6379 |
| pgbackweb | HTTP(s) | http://pgbackweb:8085 | - |

## Usage Guidelines

### For Business Users
- **Primary Tool**: NocoDB (http://localhost:8080)
- **Capabilities**: Create forms, views, dashboards without coding
- **Data Access**: Based on assigned role (Viewer/Editor/Creator)

### For Developers
- **Primary Tool**: pgAdmin (http://localhost:8081)
- **Capabilities**: Full SQL access, schema management, performance tuning
- **Backup Access**: pgbackweb for restore operations

### For DevOps Teams
- **Monitoring**: Uptime Kuma (http://localhost:3001)
- **Backups**: pgbackweb (http://localhost:8085)
- **Performance**: Monitor connection pooling via PgBouncer

## Maintenance

### Daily Operations

```bash
# Check service health
docker compose ps

# View service logs
docker compose logs <service_name>

# Restart specific service
docker compose restart <service_name>
```

### Backup Operations

```bash
# Manual database backup
docker compose exec postgres pg_dump -U postgres root_db > backup_$(date +%Y%m%d).sql

# Restore from backup
docker compose exec -T postgres psql -U postgres root_db < backup_file.sql
```

### Updates

```bash
# Pull latest images
docker compose pull

# Restart with new images
docker compose up -d
```

## Troubleshooting

### Common Issues

**NocoDB can't connect to PostgreSQL:**
```bash
# Check postgres container health
docker compose ps postgres

# Verify connection from NocoDB container
docker compose exec nocodb ping postgres
```

**pgAdmin connection refused:**
```bash
# Check if postgres is ready
docker compose exec postgres pg_isready -U postgres

# Check environment variables
docker compose exec postgres env | grep POSTGRES
```

**Services can't communicate:**
```bash
# Check network
docker network ls
docker network inspect <network_name>

# Verify DNS resolution
docker compose exec nocodb nslookup postgres
```

### Performance Tuning

**PostgreSQL Optimization:**
```sql
-- Connect via pgAdmin and run:
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

**PgBouncer Configuration:**
- Default pool size: 25 connections
- Pool mode: Transaction level
- Adjust in docker-compose.yml if needed

### Monitoring & Alerts

Set up alerts in Uptime Kuma for:
- Service downtime (> 1 minute)
- High response times (> 5 seconds)
- Failed backup jobs
- Database connection issues

## Security Considerations

1. **Change default passwords** in .env file
2. **Limit network access** - bind to 127.0.0.1 for local access only
3. **Enable SSL** for production deployments
4. **Regular backups** - automated via pgbackweb
5. **User permissions** - assign minimal required roles in NocoDB

## Scaling

### Horizontal Scaling
- Add multiple NocoDB instances behind load balancer
- Use external PostgreSQL service (AWS RDS, etc.)
- Deploy Redis cluster for high availability

### Vertical Scaling
- Increase PostgreSQL memory limits
- Adjust PgBouncer pool sizes
- Add more CPU/RAM to host

## File Structure

```
data-stack/
├── docker-compose.yml
├── .env
├── .env.example
├── README.md
├── init-scripts/
│   └── 01-create-nocodb-db.sql
├── backups/
└── config/
```

## Support

- **NocoDB**: https://docs.nocodb.com
- **PostgreSQL**: https://postgresql.org/docs
- **pgAdmin**: https://pgadmin.org/docs
- **Docker Compose**: https://docs.docker.com/compose

## License

This configuration is provided as-is for educational and production use.