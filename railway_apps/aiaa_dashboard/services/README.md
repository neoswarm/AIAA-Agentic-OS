# AIAA Dashboard Services

Business logic and external service integrations for the AIAA dashboard.

## Deployment Service

The `deployment_service.py` module handles programmatic deployment of workflows to Railway.

### Features

- **One-click deployment** - Deploy any skill to Railway with a single API call
- **Railway GraphQL API** - Full integration with Railway's v2 GraphQL API
- **Service scaffolding** - Automatic generation of Railway configuration files
- **Environment management** - Set environment variables per service
- **Cron scheduling** - Configure cron schedules for automated workflows
- **Domain generation** - Automatic public domain creation for webhooks/web services
- **Health checking** - Monitor deployed service health
- **Rollback support** - Rollback to previous deployments

### Usage Example

```python
from services import DeploymentService

# Initialize
service = DeploymentService(
    railway_api_token=os.getenv('RAILWAY_API_TOKEN'),
    project_id=os.getenv('RAILWAY_PROJECT_ID'),
    environment_id='production'
)

# Deploy a workflow
result = service.deploy_workflow(
    workflow_name='cold-email-campaign',
    workflow_type='cron',
    config={
        'name': 'Cold Email Automation',
        'description': 'Daily cold email campaign execution',
        'schedule': '0 9 * * *',
        'env_vars': {
            'OPENROUTER_API_KEY': 'sk-...',
            'PERPLEXITY_API_KEY': 'pplx-...'
        }
    }
)

print(result['status'])  # 'success' or 'error'
print(result['service_id'])
print(result['service_url'])
```

### Configuration

Required environment variables:

```bash
RAILWAY_API_TOKEN=your_token_here
RAILWAY_PROJECT_ID=3b96c81f-9518-4131-b2bc-bcd7a524a5ef
RAILWAY_ENV_ID=production  # optional, defaults to 'production'
```

### Railway GraphQL API Reference

The service uses these Railway GraphQL mutations:

1. **serviceCreate** - Create new service
2. **variableUpsert** - Set environment variables
3. **serviceInstanceUpdate** - Update service config (cron schedule)
4. **serviceDomainCreate** - Generate public domain
5. **deploymentCreate** - Trigger deployment
6. **deploymentRedeploy** - Rollback to previous deployment

### Workflow Types

- **cron** - Scheduled execution (e.g., daily email campaigns)
- **webhook** - HTTP webhook endpoint (e.g., Calendly → Slack)
- **web** - Web service with public URL (e.g., dashboard, API)

### Error Handling

The service returns standardized error responses:

```python
{
    "status": "error",
    "message": "Detailed error message here"
}
```

Common errors:
- Missing Railway credentials
- Invalid workflow name
- Missing required environment variables
- Railway API timeout
- Deployment failures

### Testing

```bash
# Test deployment locally
python3 -c "
from services import DeploymentService
service = DeploymentService('token', 'project_id', 'prod')
result = service.deploy_workflow('cold-email-campaign', 'cron', {})
print(result)
"
```

### Railway Free Tier Limits

- 8 web endpoints max
- 500 hours/month execution time
- $5 credit/month
- No credit card required

Plan deployments accordingly to stay within limits.

## Future Services

- **monitoring_service.py** - Track service health and metrics
- **logging_service.py** - Centralized logging aggregation
- **analytics_service.py** - Usage analytics and reporting
- **notification_service.py** - Multi-channel notifications (Slack, email, SMS)
