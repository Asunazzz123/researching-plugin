#!/usr/bin/env node

import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const ALPHAXIV_URL = "https://api.alphaxiv.org/mcp/v1";
const PROTOCOL_VERSION = "2025-06-18";

const REMOTE_ARGS = [
  "-y",
  "mcp-remote@0.1.38",
  ALPHAXIV_URL,
  "--transport",
  "http-only",
  "--ignore-tool",
  "list_library",
  "--ignore-tool",
  "save_papers_to_folder",
  "--ignore-tool",
  "remove_papers_from_folder",
  "--ignore-tool",
  "move_papers_between_folders",
  "--ignore-tool",
  "create_folder",
  "--ignore-tool",
  "rename_folder",
  "--ignore-tool",
  "delete_folder",
];

export const ALPHAXIV_TOOLS = [
  {
    name: "discover_papers",
    description:
      "Discover and rank arXiv papers for a research question using alphaXiv semantic retrieval.",
    inputSchema: {
      type: "object",
      properties: {
        keywords: {
          type: "array",
          items: { type: "string" },
          description: "Three or four concise exact-match terms.",
        },
        question: {
          type: "string",
          description: "Detailed semantic description of the desired papers.",
        },
        difficulty: {
          type: "number",
          minimum: 1,
          maximum: 10,
          description: "Retrieval effort from 1 to 10.",
        },
        published_after: {
          type: "string",
          description: "Optional inclusive lower date bound in YYYY-MM-DD form.",
        },
        published_before: {
          type: "string",
          description: "Optional inclusive upper date bound in YYYY-MM-DD form.",
        },
        prioritize: {
          type: "string",
          enum: ["default", "historical", "recency"],
        },
      },
      required: ["keywords", "question", "difficulty"],
      additionalProperties: false,
    },
  },
  {
    name: "get_paper_content",
    description:
      "Read an arXiv or alphaXiv paper as a generated report or full extracted text.",
    inputSchema: {
      type: "object",
      properties: {
        url: { type: "string", description: "An arXiv or alphaXiv paper URL." },
        fullText: {
          type: "boolean",
          description: "Return full extracted text instead of the generated report.",
        },
      },
      required: ["url"],
      additionalProperties: false,
    },
  },
  {
    name: "answer_pdf_queries",
    description: "Return page-level PDF content relevant to one or more questions.",
    inputSchema: {
      type: "object",
      properties: {
        paper: { type: "string", description: "Paper ID, title, or URL." },
        queries: {
          type: "array",
          items: { type: "string" },
          description: "Questions to answer from the paper pages.",
        },
      },
      required: ["paper", "queries"],
      additionalProperties: false,
    },
  },
  {
    name: "read_files_from_github_repository",
    description: "Read files or directories from a paper's GitHub repository.",
    inputSchema: {
      type: "object",
      properties: {
        githubUrl: { type: "string", description: "GitHub repository URL." },
        path: { type: "string", description: "File or directory path; use / for the root." },
      },
      required: ["githubUrl", "path"],
      additionalProperties: false,
    },
  },
];

const ALLOWED_TOOLS = new Set(ALPHAXIV_TOOLS.map(({ name }) => name));

class JsonLinePeer {
  constructor(child) {
    this.child = child;
    this.buffer = "";
    this.nextId = 1;
    this.pending = new Map();

    child.stdout.setEncoding("utf8");
    child.stdout.on("data", (chunk) => this.consume(chunk));
    child.stderr.pipe(process.stderr);
    child.once("exit", (code, signal) => {
      const reason = `alphaXiv bridge exited (code=${code}, signal=${signal})`;
      for (const { reject } of this.pending.values()) {
        reject(new Error(reason));
      }
      this.pending.clear();
    });
    child.once("error", (error) => {
      for (const { reject } of this.pending.values()) {
        reject(error);
      }
      this.pending.clear();
    });
  }

  consume(chunk) {
    this.buffer += chunk;
    while (true) {
      const newline = this.buffer.indexOf("\n");
      if (newline === -1) return;
      const line = this.buffer.slice(0, newline).trim();
      this.buffer = this.buffer.slice(newline + 1);
      if (!line) continue;

      let message;
      try {
        message = JSON.parse(line);
      } catch {
        continue;
      }

      if (message.id === undefined) continue;
      const waiter = this.pending.get(message.id);
      if (!waiter) continue;
      this.pending.delete(message.id);
      if (message.error) {
        waiter.reject(new Error(message.error.message || "Remote MCP request failed"));
      } else {
        waiter.resolve(message.result);
      }
    }
  }

  send(message) {
    this.child.stdin.write(`${JSON.stringify(message)}\n`);
  }

  notify(method, params = {}) {
    this.send({ jsonrpc: "2.0", method, params });
  }

  request(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.send({ jsonrpc: "2.0", id, method, params });
    });
  }

  close() {
    if (!this.child.killed) this.child.kill("SIGTERM");
  }
}

async function connectRemote() {
  const child = spawn("npx", REMOTE_ARGS, {
    stdio: ["pipe", "pipe", "pipe"],
    env: {
      ...process.env,
      npm_config_cache:
        process.env.npm_config_cache || join(tmpdir(), "alphaxiv-npm-cache"),
    },
  });
  const peer = new JsonLinePeer(child);
  await peer.request("initialize", {
    protocolVersion: PROTOCOL_VERSION,
    capabilities: {},
    clientInfo: { name: "researching-plugin-lazy-bridge", version: "1.0.0" },
  });
  peer.notify("notifications/initialized");
  return peer;
}

export function createLazyAlphaXivHandler({ connect = connectRemote } = {}) {
  let remotePromise;

  const getRemote = () => {
    if (!remotePromise) {
      remotePromise = connect().catch((error) => {
        remotePromise = undefined;
        throw error;
      });
    }
    return remotePromise;
  };

  return {
    async handle(method, params = {}) {
      switch (method) {
        case "initialize":
          return {
            protocolVersion: PROTOCOL_VERSION,
            capabilities: { tools: { listChanged: false } },
            serverInfo: { name: "alphaxiv-lazy-bridge", version: "1.0.0" },
            instructions:
              "Read-only alphaXiv tools. The remote service and browser OAuth start only on the first tools/call request.",
          };
        case "ping":
          return {};
        case "tools/list":
          return { tools: ALPHAXIV_TOOLS };
        case "tools/call": {
          if (!ALLOWED_TOOLS.has(params.name)) {
            throw new Error(`Tool is not exposed by the read-only bridge: ${params.name}`);
          }
          const remote = await getRemote();
          return remote.request("tools/call", params);
        }
        default:
          throw new Error(`Method not found: ${method}`);
      }
    },
    async close() {
      if (remotePromise) {
        const remote = await remotePromise.catch(() => undefined);
        remote?.close();
      }
    },
  };
}

function writeMessage(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

async function main() {
  const handler = createLazyAlphaXivHandler();
  let buffer = "";
  let chain = Promise.resolve();

  const processLine = async (line) => {
    let message;
    try {
      message = JSON.parse(line);
    } catch {
      return;
    }

    if (message.id === undefined) return;
    try {
      const result = await handler.handle(message.method, message.params);
      writeMessage({ jsonrpc: "2.0", id: message.id, result });
    } catch (error) {
      writeMessage({
        jsonrpc: "2.0",
        id: message.id,
        error: { code: -32603, message: error instanceof Error ? error.message : String(error) },
      });
    }
  };

  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => {
    buffer += chunk;
    while (true) {
      const newline = buffer.indexOf("\n");
      if (newline === -1) break;
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (line) chain = chain.then(() => processLine(line));
    }
  });

  const shutdown = async () => {
    await handler.close();
    process.exit(0);
  };
  process.once("SIGINT", shutdown);
  process.once("SIGTERM", shutdown);
  process.stdin.once("end", shutdown);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    process.stderr.write(`${error instanceof Error ? error.stack : String(error)}\n`);
    process.exit(1);
  });
}
