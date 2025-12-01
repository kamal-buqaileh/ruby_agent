# Ruby Agent Docker Setup

## Building the Image

You can build from the ruby_agent directory:

```bash
cd ruby_agent
docker build -t ruby-agent .
```

## Running the Agent

### 1. Setup (First Time)

**Important:** Mount your project directory before running setup so the container can access it.

Run the interactive setup to configure the agent:

```bash
# Mount your workspace/projects directory
docker run -it --rm \
  -v ~/.ruby_agent:/root/.ruby_agent \
  -v ~/workspace:/workspace:ro \
  -e DOCKER_CONTAINER=true \
  ruby-agent python -m ruby_agent.main --setup
```

**During setup, use container paths:**
- If you mounted `~/workspace` to `/workspace`, use `/workspace/your-project`
- The setup will detect you're in Docker and guide you accordingly

### 2. Run as Server

Start the HTTP server to receive requests:

```bash
docker run -d --name ruby-agent \
  -p 8000:8000 \
  -v ~/.ruby_agent:/root/.ruby_agent \
  -v $(pwd)/output:/app/output \
  -v ~/workspace:/workspace:ro \
  -e DOCKER_CONTAINER=true \
  ruby-agent python -m ruby_agent.main --server --host 0.0.0.0 --port 8000
```

**Note:** Make sure to mount the same workspace directory you used during setup.

### 3. Analyze a Project

Analyze a Ruby project:

```bash
docker run --rm \
  -v ~/.ruby_agent:/root/.ruby_agent \
  -v $(pwd)/output:/app/output \
  -v /path/to/your/project:/workspace/project:ro \
  ruby-agent python -m ruby_agent.main /workspace/project -o output/nodes.json
```

### 4. Using Docker Compose

Start the server:

```bash
docker-compose up -d
```

Run setup:

```bash
docker-compose run --rm ruby-agent python -m ruby_agent.main --setup
```

## API Endpoints

Once the server is running, you can:

- **Health Check**: `GET http://localhost:8000/health`
- **Analyze**: `POST http://localhost:8000/analyze`
  ```json
  {
    "root": "/workspace/project",
    "output": "output/nodes.json"
  }
  ```

## Notes

- Configuration is persisted in `~/.ruby_agent/config.json`
- Output files are saved to `./output/` directory
- The server binds to `0.0.0.0` to accept connections from outside the container
