# MCP study plan: Mon 26 Oct – Sun 1 Nov 2026

Evenings, 9–11 pm PKT. Every link was opened and confirmed to load on 25 Oct 2026. All resources are free.

| Day | Topic | Time | Resource |
|---|---|---|---|
| **Mon 26 Oct** | How MCP works: hosts, clients, servers, and the two layers (data and transport) | 2 h | [MCP Architecture overview](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture.md) (official docs) + [Hugging Face MCP Course intro](https://huggingface.co/learn/mcp-course/en/unit0/introduction) (free) |
| **Tue 27 Oct** | A server's three building blocks: tools, resources, prompts | 1.5 h | [Understanding MCP servers](https://modelcontextprotocol.io/docs/2026-07-28/learn/server-concepts.md) (official docs) |
| **Wed 28 Oct** | Use a ready-made server first: connect the Filesystem server to Claude Desktop | 2 h | [Connect to local MCP servers](https://modelcontextprotocol.io/docs/2026-07-28/develop/connect-local-servers.md) (official docs; has Windows steps) |
| **Thu 29 Oct** | Build your first server in Python: a weather server with two tools | 2 h | [Build an MCP server](https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server.md) (official quickstart) |
| **Fri 30 Oct** | **Rest day** | — | — |
| **Sat 31 Oct** | Test and debug a server with MCP Inspector, then build a second practice server (calculator) | 2 h | [MCP Inspector docs](https://modelcontextprotocol.io/docs/tools/inspector.md) + [Microsoft MCP for Beginners: first server](https://github.com/microsoft/mcp-for-beginners/blob/main/03-GettingStarted/01-first-server/README.md) |
| **Sun 1 Nov** | Build your own small server (e.g. a study-notes tool), connect it to Claude Desktop, and review | 2 h | [Anthropic Academy: Introduction to MCP](https://anthropic.skilljar.com/introduction-to-model-context-protocol) (free, Python) |

**Total:** 11.5 hours over six study days.

## Why this order

Understand the parts → use a server someone else built → build one from a tutorial → debug it → build your own. The rest day falls after the first build, before the debugging day.

## Before you start

- **Setup:** Days 3, 4 and 6 need **Node.js 22.19 or newer** (for the Inspector) and Python with **uv**. Installing these takes time; consider doing it on Tuesday after reading.
- **Day 4:** the weather tutorial uses the US National Weather Service API. It's free and needs no key, but only returns **US** forecasts, so test with US places.
- **Accounts:** Anthropic Academy needs a free Skilljar account; the Hugging Face course needs a free Hugging Face account.
- **Left out because paid:** a Udemy MCP course and several Packt videos appeared in search; excluded, since the brief says to ask first.

## Risks

- **Anthropic Academy:** the page loaded but showed "video still processing" and "rate limit" errors. Try it before Sunday; fall back to the Hugging Face course.
- **Claude Desktop plan support:** the official page doesn't say which plans run local servers. Test on Wednesday. If it won't connect, the Inspector (Saturday) can test your server without Claude Desktop.
