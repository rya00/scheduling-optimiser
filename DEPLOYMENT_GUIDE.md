# Deployment Guide: Scalable Staff Scheduling Tool

## Executive Summary

This document outlines the architecture and deployment strategy for scaling the staff scheduling optimization system from a proof-of-concept to a production-ready solution.

---

## 1. System Architecture

### 1.1 Proposed Architecture (Microservices)

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                      │
├─────────────────────────────────────────────────────────────────┤
│  Web Dashboard (React/Vue)  │  Mobile App  │  API for Integrations│
└─────────────┬───────────────┴──────────────┴────────────────────┘
              │
              │ HTTPS/REST API
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (Kong/AWS API Gateway)          │
└─────────────┬───────────────────────────────────────────────────┘
              │
              ├──────────────────┬──────────────────┬──────────────┐
              ▼                  ▼                  ▼              ▼
┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐  ┌─────────────┐
│ Data Ingestion   │  │ Optimization     │  │ Scheduling  │  │ Notification│
│ Service          │  │ Engine Service   │  │ Service     │  │ Service     │
│                  │  │                  │  │             │  │             │
│ - Staff Import   │  │ - MILP Solver    │  │ - Generate  │  │ - Email     │
│ - Job Import     │  │ - Constraint Mgmt│  │ - Modify    │  │ - SMS       │
│ - Validation     │  │ - Multi-objective│  │ - View      │  │ - Slack     │
│ - Historical Data│  │ - Real-time Solve│  │ - Export    │  │             │
└────────┬─────────┘  └────────┬─────────┘  └──────┬──────┘  └──────┬──────┘
         │                     │                    │                │
         └─────────────────────┴────────────────────┴────────────────┘
                                        │
                                        ▼
                      ┌──────────────────────────────────────┐
                      │   Message Queue (RabbitMQ/Kafka)     │
                      └──────────────────────────────────────┘
                                        │
                      ┌─────────────────┴─────────────────────┐
                      ▼                                       ▼
            ┌──────────────────┐                  ┌──────────────────┐
            │  PostgreSQL      │                  │  Redis Cache     │
            │  - Staff DB      │                  │  - Session Data  │
            │  - Job DB        │                  │  - Results Cache │
            │  - Schedule DB   │                  │  - Rate Limiting │
            │  - Audit Logs    │                  └──────────────────┘
            └──────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │  S3/Blob Storage │
            │  - Historical Data│
            │  - Reports        │
            │  - Backups        │
            └──────────────────┘
```

---

## 2. Technology Stack Recommendations

### 2.1 Core Components

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Backend API** | FastAPI (Python) or Node.js + Express | High performance, async support, native Python integration |
| **Optimization Engine** | PuLP + CBC or Gurobi | Open-source (CBC) or commercial (Gurobi) for larger problems |
| **Database** | PostgreSQL with PostGIS | ACID compliance, JSON support, geospatial queries |
| **Cache** | Redis | Fast in-memory caching for frequent queries |
| **Message Queue** | RabbitMQ or Apache Kafka | Asynchronous task processing |
| **Frontend** | React + TypeScript | Modern, component-based, strong typing |
| **API Gateway** | Kong or AWS API Gateway | Rate limiting, authentication, routing |
| **Container Orchestration** | Kubernetes (EKS/GKE/AKS) | Scalability, self-healing, load balancing |
| **Monitoring** | Prometheus + Grafana | Metrics, alerting, visualization |
| **Logging** | ELK Stack (Elasticsearch, Logstash, Kibana) | Centralized logging |

### 2.2 Cloud Provider Options

**AWS Architecture:**
- ECS/EKS for containers
- RDS for PostgreSQL
- ElastiCache for Redis
- S3 for storage
- SQS/SNS for messaging
- Lambda for serverless tasks
- CloudWatch for monitoring

**GCP Architecture:**
- GKE for Kubernetes
- Cloud SQL for PostgreSQL
- Memorystore for Redis
- Cloud Storage
- Pub/Sub for messaging
- Cloud Functions
- Operations Suite for monitoring

**Azure Architecture:**
- AKS for Kubernetes
- Azure Database for PostgreSQL
- Azure Cache for Redis
- Blob Storage
- Service Bus
- Azure Functions
- Application Insights

---

## 3. Scalability Strategies

### 3.1 Horizontal Scaling

**Optimization Engine Scaling:**
- Deploy multiple solver instances behind a load balancer
- Use job queuing system for large optimization requests
- Implement timeout and retry logic
- Cache frequently requested solutions

```python
# Example: Celery task for distributed solving
from celery import Celery

app = Celery('scheduler', broker='redis://localhost:6379')

@app.task
def optimize_schedule(job_data, staff_data, constraints):
    optimizer = StaffSchedulingOptimizer(job_data, staff_data)
    optimizer.build_optimization_model(**constraints)
    result = optimizer.solve_optimization()
    return result
```

**Database Scaling:**
- Read replicas for analytics queries
- Sharding by region or time period
- Partitioning large tables (e.g., historical assignments)
- Connection pooling (PgBouncer)

### 3.2 Performance Optimization

**Problem Size Management:**
1. **Decomposition**: Break large problems into smaller subproblems
   - Geographic decomposition (by region)
   - Temporal decomposition (by time period)
   - Hierarchical solving (high priority first)

2. **Heuristic Approaches**: For very large problems (>10,000 jobs)
   - Genetic algorithms
   - Simulated annealing
   - Tabu search
   - Column generation

3. **Warm Starting**: Use previous solutions as starting points

```python
# Example: Regional decomposition
def optimize_by_region(jobs_df, staff_df):
    results = []
    for region in jobs_df['Job_Location'].unique():
        regional_jobs = jobs_df[jobs_df['Job_Location'] == region]
        regional_staff = find_nearby_staff(staff_df, region)

        optimizer = StaffSchedulingOptimizer(regional_jobs, regional_staff)
        regional_solution = optimizer.solve_optimization()
        results.append(regional_solution)

    return merge_regional_solutions(results)
```

### 3.3 Caching Strategy

**Multi-Level Caching:**
1. **L1**: Browser cache (static assets)
2. **L2**: CDN cache (images, reports)
3. **L3**: Redis cache (API responses, partial solutions)
4. **L4**: Database query cache

**Cache Invalidation:**
- Time-based expiration
- Event-driven invalidation
- Version-based cache keys

---

## 4. API Design

### 4.1 RESTful Endpoints

```
POST   /api/v1/schedules/optimize
GET    /api/v1/schedules/{schedule_id}
GET    /api/v1/schedules/{schedule_id}/status
PUT    /api/v1/schedules/{schedule_id}/assignments/{assignment_id}
DELETE /api/v1/schedules/{schedule_id}

POST   /api/v1/jobs
GET    /api/v1/jobs
GET    /api/v1/jobs/{job_id}
PUT    /api/v1/jobs/{job_id}

POST   /api/v1/staff
GET    /api/v1/staff
GET    /api/v1/staff/{staff_id}
PUT    /api/v1/staff/{staff_id}
GET    /api/v1/staff/{staff_id}/workload

GET    /api/v1/analytics/performance
GET    /api/v1/analytics/costs
GET    /api/v1/analytics/satisfaction
```

### 4.2 Example API Request

```json
POST /api/v1/schedules/optimize

{
  "name": "Week 45 Schedule",
  "start_date": "2025-11-03",
  "end_date": "2025-11-09",
  "job_ids": ["J001", "J002", "J003"],
  "staff_pool": ["S001", "S002", "S003"],
  "constraints": {
    "min_skill_match": 0.6,
    "max_jobs_per_staff": 5,
    "max_distance_km": 200
  },
  "objectives": {
    "cost_weight": 0.6,
    "satisfaction_weight": 0.2,
    "skill_weight": 0.2
  },
  "options": {
    "time_limit_seconds": 300,
    "parallel_regions": true
  }
}
```

### 4.3 Response Format

```json
{
  "schedule_id": "sch_20251103_xyz",
  "status": "completed",
  "created_at": "2025-11-03T10:00:00Z",
  "solved_at": "2025-11-03T10:05:23Z",
  "solver_time_seconds": 323,
  "metrics": {
    "total_cost": 312430.85,
    "travel_cost": 68441.85,
    "labour_cost": 243989.00,
    "avg_satisfaction": 3.01,
    "avg_skill_match": 0.748,
    "jobs_assigned": 1000,
    "staff_utilized": 250
  },
  "assignments": [
    {
      "assignment_id": "asn_001",
      "staff_id": "S001",
      "job_id": "J001",
      "job_location": "London",
      "skill_match": 0.85,
      "total_cost": 345.50
    }
  ],
  "download_url": "/api/v1/schedules/sch_20251103_xyz/download"
}
```

---

## 5. Data Model

### 5.1 Database Schema

```sql
-- Staff Table
CREATE TABLE staff (
    staff_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    location GEOGRAPHY(POINT),
    years_experience INTEGER,
    absenteeism_days INTEGER,
    satisfaction_score DECIMAL(3,2),
    cost_per_hour DECIMAL(10,2),
    skills JSONB,
    max_jobs_per_period INTEGER DEFAULT 5,
    available_dates JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Jobs Table
CREATE TABLE jobs (
    job_id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    location GEOGRAPHY(POINT),
    location_name VARCHAR(255),
    priority INTEGER CHECK (priority BETWEEN 1 AND 5),
    required_skills JSONB,
    hours_required INTEGER,
    start_date DATE,
    deadline DATE,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Schedules Table
CREATE TABLE schedules (
    schedule_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    start_date DATE,
    end_date DATE,
    status VARCHAR(50),
    solver_status VARCHAR(50),
    solver_time_seconds INTEGER,
    constraints JSONB,
    objectives JSONB,
    metrics JSONB,
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    solved_at TIMESTAMP
);

-- Assignments Table
CREATE TABLE assignments (
    assignment_id VARCHAR(50) PRIMARY KEY,
    schedule_id VARCHAR(50) REFERENCES schedules(schedule_id) ON DELETE CASCADE,
    staff_id VARCHAR(50) REFERENCES staff(staff_id),
    job_id VARCHAR(50) REFERENCES jobs(job_id),
    skill_match DECIMAL(3,2),
    distance_km DECIMAL(10,2),
    travel_cost DECIMAL(10,2),
    labour_cost DECIMAL(10,2),
    total_cost DECIMAL(10,2),
    assigned_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'assigned'
);

-- Historical Performance Table
CREATE TABLE performance_history (
    id SERIAL PRIMARY KEY,
    assignment_id VARCHAR(50) REFERENCES assignments(assignment_id),
    actual_hours INTEGER,
    quality_score DECIMAL(3,2),
    client_satisfaction DECIMAL(3,2),
    completed_on_time BOOLEAN,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_staff_location ON staff USING GIST(location);
CREATE INDEX idx_jobs_location ON jobs USING GIST(location);
CREATE INDEX idx_assignments_schedule ON assignments(schedule_id);
CREATE INDEX idx_assignments_staff ON assignments(staff_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_schedules_dates ON schedules(start_date, end_date);
```

### 5.2 Data Relationships

```
staff (1) ──────< (N) assignments (N) >────── (1) jobs
                         │
                         │
                         v
                    schedules (1)
                         │
                         │
                         v
                  performance_history (N)
```

---

## 6. Security & Compliance

### 6.1 Authentication & Authorization

- **OAuth 2.0 / OpenID Connect** for user authentication
- **JWT tokens** for API authentication
- **Role-Based Access Control (RBAC)**:
  - Admin: Full access
  - Manager: Create/view/edit schedules
  - Staff: View assigned jobs only
  - Client: View job status

### 6.2 Data Protection

- **Encryption at rest**: Database encryption (TDE)
- **Encryption in transit**: TLS 1.3
- **PII handling**: Anonymization for analytics
- **GDPR compliance**: Right to deletion, data portability
- **Audit logging**: All API calls, data modifications

### 6.3 Rate Limiting

```python
# Example rate limiting configuration
RATE_LIMITS = {
    'optimization': '5 per hour',     # Expensive operations
    'api_read': '1000 per hour',
    'api_write': '100 per hour',
}
```

---

## 7. Monitoring & Observability

### 7.1 Key Metrics

**Business Metrics:**
- Schedules created per day
- Average optimization time
- Cost savings vs baseline
- Staff utilization rate
- Client satisfaction scores

**Technical Metrics:**
- API response time (p50, p95, p99)
- Error rate
- Solver success rate
- Database query performance
- Cache hit ratio
- Queue depth

### 7.2 Alerting Rules

```yaml
# Example Prometheus alerting rules
groups:
  - name: scheduler_alerts
    rules:
      - alert: HighAPILatency
        expr: http_request_duration_seconds{quantile="0.95"} > 2
        for: 5m
        annotations:
          summary: "API latency is high"

      - alert: SolverFailureRate
        expr: rate(solver_failures[5m]) > 0.1
        annotations:
          summary: "High solver failure rate"

      - alert: DatabaseConnectionPool
        expr: db_connections_in_use / db_connections_max > 0.8
        annotations:
          summary: "Database connection pool near capacity"
```

---

## 8. Disaster Recovery & Business Continuity

### 8.1 Backup Strategy

- **Database**: Daily full backups, hourly incremental
- **Retention**: 30 days hot, 1 year cold storage
- **Recovery Time Objective (RTO)**: < 4 hours
- **Recovery Point Objective (RPO)**: < 1 hour

### 8.2 High Availability

- **Multi-AZ deployment** for database and services
- **Auto-scaling groups** for compute resources
- **Load balancer health checks**
- **Graceful degradation**: Fallback to heuristic methods if MILP fails

---

## 9. CI/CD Pipeline

```yaml
# Example GitHub Actions workflow
name: Deploy Scheduling Tool

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run unit tests
        run: pytest tests/
      - name: Run integration tests
        run: pytest integration_tests/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker image
        run: docker build -t scheduler:${{ github.sha }} .
      - name: Push to registry
        run: docker push scheduler:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: kubectl apply -f k8s/
      - name: Run smoke tests
        run: ./smoke_tests.sh
```

---

## 10. Cost Optimization

### 10.1 Infrastructure Costs

**Estimated Monthly Costs (AWS, 10,000 jobs/day):**

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| ECS/EKS | 10 t3.medium instances | $500 |
| RDS PostgreSQL | db.m5.xlarge, Multi-AZ | $400 |
| ElastiCache Redis | cache.m5.large | $150 |
| S3 | 1TB storage, 10TB transfer | $100 |
| Data Transfer | Inter-AZ, Internet | $200 |
| **Total** | | **~$1,350/month** |

### 10.2 Optimization Strategies

1. **Reserved Instances**: 40-60% savings on compute
2. **Spot Instances**: For non-critical batch processing
3. **Auto-scaling**: Scale down during off-peak hours
4. **Data lifecycle**: Archive old schedules to S3 Glacier
5. **Caching**: Reduce database queries by 70-80%

---

## 11. Roadmap to Production

### Phase 1: MVP (Months 1-2)
- [ ] Core API with authentication
- [ ] Basic MILP solver integration
- [ ] PostgreSQL database
- [ ] Simple web interface
- [ ] Manual job/staff import

### Phase 2: Enhanced Features (Months 3-4)
- [ ] Real-time optimization status
- [ ] Email notifications
- [ ] CSV import/export
- [ ] Performance analytics dashboard
- [ ] Redis caching

### Phase 3: Scalability (Months 5-6)
- [ ] Message queue for async processing
- [ ] Multi-region support
- [ ] Advanced solver options (parallel, heuristics)
- [ ] API rate limiting
- [ ] Comprehensive monitoring

### Phase 4: Enterprise Features (Months 7-9)
- [ ] SSO integration
- [ ] Advanced RBAC
- [ ] Audit logging
- [ ] Mobile app
- [ ] Machine learning for demand forecasting
- [ ] What-if scenario planning

---

## 12. Success Metrics

**Year 1 Targets:**
- 99.5% uptime SLA
- Average optimization time < 5 minutes for 1,000 jobs
- 15% cost reduction vs manual scheduling
- 20% improvement in staff satisfaction
- 90% skill match accuracy
- 100,000 jobs scheduled

---

## 13. Next Steps

1. **Infrastructure Setup**: Provision cloud resources
2. **API Development**: Implement FastAPI backend
3. **Frontend Development**: Build React dashboard
4. **Integration Testing**: Test with real data
5. **Beta Launch**: Deploy to pilot users
6. **Monitoring Setup**: Configure Prometheus/Grafana
7. **Documentation**: API docs, user guides
8. **Training**: Staff training sessions
9. **Go-Live**: Production launch
10. **Iteration**: Continuous improvement based on feedback

---

## Appendix A: Sample Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scheduler-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scheduler-api
  template:
    metadata:
      labels:
        app: scheduler-api
    spec:
      containers:
      - name: api
        image: scheduler:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secrets
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: scheduler-api
spec:
  selector:
    app: scheduler-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## Appendix B: Environment Variables

```bash
# Application
APP_ENV=production
APP_DEBUG=false
LOG_LEVEL=info

# Database
DATABASE_URL=postgresql://user:pass@host:5432/scheduler
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Solver
SOLVER_ENGINE=cbc  # or 'gurobi'
SOLVER_TIME_LIMIT=300
SOLVER_THREADS=4

# API
API_RATE_LIMIT=1000
API_TIMEOUT=30

# Authentication
JWT_SECRET=your-secret-key
JWT_EXPIRATION=3600
OAUTH_CLIENT_ID=your-client-id

# Monitoring
PROMETHEUS_PORT=9090
SENTRY_DSN=https://...

# Cloud
AWS_REGION=us-east-1
S3_BUCKET=scheduler-data
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-27
**Author**: Operations Research Team
