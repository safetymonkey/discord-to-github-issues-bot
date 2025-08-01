# Discord-to-GitHub Issues Bot

A containerized Discord bot that allows server administrators to create GitHub issues directly from Discord messages using slash commands. Built with modern Python tooling (uv) and designed for container deployment.

## Features

- 🤖 **Discord Integration**: Create GitHub issues from Discord messages via `/create-issue` slash command
- 🔒 **Permission Control**: Administrator-only access to issue creation
- 🏷️ **Flexible Labeling**: Add custom labels and assignees to issues
- 📊 **Database Tracking**: SQLite database to link Discord messages with GitHub issues
- 🐳 **Container Ready**: Optimized Docker containers with multi-stage builds
- 🔧 **Modern Tooling**: Built with uv for fast dependency management
- 📋 **Health Monitoring**: Built-in health checks for container orchestration
- 🛡️ **Security**: Non-root container execution and graceful shutdown handling

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose
- Discord Bot Token
- GitHub Personal Access Token with `repo` permissions
- Target GitHub repository

### 1. Clone and Configure

```bash
git clone <your-repository-url>
cd discord-to-github-issues-bot

# Copy environment template
cp .env.example .env

# Edit .env with your tokens and repository details
```

### 2. Run with Docker Compose

```bash
# Build and start the bot
docker-compose up -d

# View logs
docker-compose logs -f discord-bot

# Stop the bot
docker-compose down
```

## Development Setup

### Prerequisites

- Python 3.8+
- [uv](https://docs.astral.sh/uv/) package manager

### Local Development

```bash
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Run the bot
uv run python -m src.bot

# Run tests
uv run pytest

# Run with development dependencies
uv sync --dev
uv run pytest --cov=src
```

## Configuration

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DISCORD_TOKEN` | ✅ | Discord bot token | `MTEx...` |
| `GITHUB_TOKEN` | ✅ | GitHub personal access token | `ghp_...` |
| `GITHUB_REPO_OWNER` | ✅ | GitHub repository owner | `your-username` |
| `GITHUB_REPO_NAME` | ✅ | GitHub repository name | `your-repo` |
| `DATABASE_PATH` | ❌ | Database file path | `/app/data/bot_data.db` |

### Discord Bot Setup

1. Create a new application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a bot user and copy the token
3. Enable the following bot permissions:
   - Read Messages/View Channels
   - Send Messages
   - Use Slash Commands
4. Invite the bot to your server with Administrator permissions

### GitHub Setup

1. Create a [Personal Access Token](https://github.com/settings/tokens) with `repo` scope
2. Ensure the token has access to the target repository

## Usage

Once the bot is running and invited to your Discord server:

### `/create-issue` Command

Create a GitHub issue from any Discord message:

```
/create-issue message_id:123456789 title:"Bug Report" labels:"bug,urgent" assignees:"username1,username2"
```

**Parameters:**
- `message_id` (required): Discord message ID to convert to issue
- `title` (required): GitHub issue title
- `labels` (optional): Comma-separated list of labels
- `assignees` (optional): Comma-separated list of GitHub usernames

### `/health` Command

Check bot health status (admin only):

```
/health
```

## Container Deployment

### Docker

```bash
# Build the image
docker build -t discord-github-bot .

# Run with environment variables
docker run -d \
  --name discord-bot \
  -e DISCORD_TOKEN="your_token" \
  -e GITHUB_TOKEN="your_token" \
  -e GITHUB_REPO_OWNER="owner" \
  -e GITHUB_REPO_NAME="repo" \
  -v bot_data:/app/data \
  discord-github-bot
```

### Production Deployment

For production environments, consider:

- **Database**: Use PostgreSQL instead of SQLite (uncomment postgres service in docker-compose.yml)
- **Secrets Management**: Use Docker secrets or Kubernetes secrets
- **Monitoring**: Configure logging aggregation and health check endpoints
- **Resource Limits**: Adjust memory and CPU limits in docker-compose.yml
- **Backup**: Regular database backups if using SQLite with persistent volumes

### Kubernetes Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: discord-github-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: discord-github-bot
  template:
    metadata:
      labels:
        app: discord-github-bot
    spec:
      containers:
      - name: bot
        image: discord-github-bot:latest
        env:
        - name: DISCORD_TOKEN
          valueFrom:
            secretKeyRef:
              name: bot-secrets
              key: discord-token
        # ... other env vars
        volumeMounts:
        - name: data
          mountPath: /app/data
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: bot-data-pvc
```

## Development

### Project Structure

```
discord-to-github-issues-bot/
├── src/
│   ├── db/
│   │   └── database.py      # Database operations
│   └── bot.py               # Main bot logic
├── tests/
│   ├── __init__.py
│   └── test_bot.py          # Test cases
├── Dockerfile               # Container definition
├── docker-compose.yml       # Local development setup
├── pyproject.toml          # Python dependencies and metadata
├── .env.example            # Environment template
└── README.md
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run tests: `uv run pytest`
6. Submit a pull request

### Testing

Run the test suite:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_bot.py -v
```

## Troubleshooting

### Common Issues

1. **Bot not responding to slash commands**
   - Ensure the bot has been invited with proper permissions
   - Check that slash commands are synced (see bot logs)
   - Verify the bot token is correct

2. **GitHub API errors**
   - Verify GitHub token has `repo` permissions
   - Check repository owner/name are correct
   - Ensure the token hasn't expired

3. **Database errors**
   - Check that the data directory exists and is writable
   - For containers, verify volume mounting is correct

4. **Container startup issues**
   - Check container logs: `docker-compose logs discord-bot`
   - Verify all environment variables are set
   - Ensure Docker has enough resources allocated

### Logs

View bot logs:

```bash
# Docker Compose
docker-compose logs -f discord-bot

# Docker
docker logs -f <container-id>

# Local development
# Logs output to stdout with structured formatting
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Search existing GitHub issues
3. Create a new issue with detailed information about your setup and the problem
