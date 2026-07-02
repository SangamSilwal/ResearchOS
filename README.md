# ResearchOS

<div align="center">

![License](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/Python-3.14+-3776AB?logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-Framework-1C3C3C)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-purple)
![LangSmith](https://img.shields.io/badge/LangSmith-Tracing-success)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange)
![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen)

</div>

<p align="center">
An autonomous multi-agent AI software engineering system built with the <b>LangChain ecosystem</b>, powered by <b>LangGraph</b>, observed with <b>LangSmith</b>, and extended using the <b>Model Context Protocol (MCP)</b>.
</p>

---

# ResearchOS

ResearchOS is an autonomous AI software engineering system built using the **LangChain ecosystem**, leveraging **LangGraph** for agent orchestration, **LangSmith** for tracing and observability, and **Model Context Protocol (MCP)** servers for external tool integration.

Given a high-level software engineering task, ResearchOS performs research, planning, code generation, and iterative review through a collaborative team of specialized AI agents.

---

## Features

- Multi-agent autonomous software engineering workflow
- Agent orchestration using **LangGraph**
- LLM abstraction through **LangChain**
- Execution tracing and debugging with **LangSmith**
- Web research using **Tavily MCP**
- Academic paper retrieval using **ArXiv MCP**
- Built on the **Model Context Protocol (MCP)**
- Fully containerized with Docker
- Generated projects are stored locally inside the `workspace/` directory

---

## Architecture

<p align="center">
  <img src="assets/multi_agent_architecture.png" alt="ResearchOS Architecture" width="100%">
</p>

The following diagram illustrates the overall ResearchOS workflow, showing how the specialized agents collaborate, interact with MCP servers, communicate with LLM providers, and produce the final software project.

## Agents

### Orchestrator

The entry point of the workflow.

Responsibilities:

- Parses the user's goal
- Breaks the objective into tasks
- Coordinates the execution graph
- Delegates work to specialized agents
- Maintains overall workflow state

---

### Research Agent

Responsible for gathering knowledge before implementation.

Capabilities:

- Searches the web using Tavily MCP
- Retrieves relevant academic papers from ArXiv
- Collects implementation references
- Produces research summaries for downstream agents

---

### Planner Agent

Transforms research into an implementation strategy.

Responsibilities:

- Creates project architecture
- Defines modules and components
- Generates implementation plans
- Determines execution order

---

### Coder Agent

Implements the planned solution.

Responsibilities:

- Generates project source code
- Creates files and directories
- Writes documentation
- Produces runnable software

---

### Critic Agent

Reviews generated outputs.

Responsibilities:

- Detects implementation issues
- Suggests improvements
- Performs quality checks
- Ensures consistency between generated artifacts

---

# Technology Stack

## AI Framework

- LangChain
- LangGraph
- LangSmith

## Model Providers

ResearchOS supports multiple LLM providers:

- Google Gemini
- Groq
- Mistral AI
- OpenRouter

---

## MCP Servers

ResearchOS currently includes:

| MCP Server | Purpose |
|------------|---------|
| Web Search MCP | Internet search powered by Tavily |
| ArXiv MCP | Academic paper retrieval |

---

# Prerequisites

Install the following before running the project:

- Docker
- Docker Compose

Verify installation:

```bash
docker --version
docker compose version
```

---

# Clone the Repository

```bash
git clone https://github.com/SangamSilwal/ResearchOS.git

cd ResearchOS
```

---

# Configure Environment Variables

Create a local environment file.

```bash
cp .env.example .env
```

Populate it with your API keys.

Example:

```env
TAVILY_API_KEY=

GOOGLE_API_KEY=

GROQ_API_KEY=

MISTRAL_API_KEY=

OPENROUTER_API_KEY=

LANGCHAIN_API_KEY=

GITHUB_TOKEN=
```

Only configure the providers you intend to use.

---

# Running ResearchOS

Start all required services.

```bash
docker compose up
```

Docker Compose will automatically:

- Pull the latest ResearchOS container image
- Start the Web Search MCP server
- Start the ArXiv MCP server
- Launch the ResearchOS agent workflow

---

# Running a Custom Task

By default the system executes:

```
Build a FastAPI service
```

To specify your own goal:

### Linux / macOS

```bash
TASK="Build an AI chatbot using FastAPI" docker compose up
```

Example:

```bash
TASK="Create an AI-powered project management application" docker compose up
```

---

# Output

Generated projects are written into:

```
workspace/
```

Example:

```
workspace/
└── project-id<number>/
    ├── backend/
    ├── frontend/
    ├── docs/
    ├── README.md
    └── ...
```

---

# Services

| Service | Port | Description |
|----------|------|-------------|
| Web Search MCP | 8000 | Tavily-powered internet search |
| ArXiv MCP | 8001 | Academic paper search |
| ResearchOS | Internal | Multi-agent software engineering workflow |

---

# Updating

Pull the newest published container image.

```bash
docker compose pull
```

Restart the project.

```bash
docker compose up
```

---

# Stopping

```bash
docker compose down
```

---

# Project Structure

```
ResearchOS/
│
├── agents/
├── core/
├── llm/
├── mcp_servers/
├── sandbox/
├── workspace/
├── run.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── README.md
└── .env.example
```

---

# Troubleshooting

## Docker Permission Denied

Add your user to the Docker group.

```bash
sudo usermod -aG docker $USER
```

Log out and log back in.

---

## Missing API Keys

Ensure all required API keys are present in your `.env` file.

---

## Updating Images

```bash
docker compose pull
```

---

# License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

See the `LICENSE` file for the complete license text.

---

# Author

**Sangam Silwal**

GitHub: https://github.com/SangamSilwal