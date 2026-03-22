#!/usr/bin/env node
/**
 * Overture Remote Access Proxy
 *
 * Bridges the gap between Overture's localhost-only UI and remote devices.
 * Fixes the hardcoded `ws://localhost:3030` in the Overture bundle by
 * patching JS responses on the fly.
 *
 * HTTP → proxied to Overture UI (port 3031), JS patched for dynamic WS host
 * WS upgrades → tunneled to Overture WebSocket server (port 3030)
 *
 * Usage:
 *   node overture-proxy.mjs
 *
 * Environment:
 *   OVERTURE_REMOTE_PORT  Port this proxy listens on  (default: 4040)
 *   OVERTURE_HTTP_PORT    Overture UI port            (default: 3031)
 *   OVERTURE_WS_PORT      Overture WebSocket port     (default: 3030)
 */

import http from 'http';
import net from 'net';

const PORT    = parseInt(process.env.OVERTURE_REMOTE_PORT || '4040', 10);
const UI_PORT = parseInt(process.env.OVERTURE_HTTP_PORT   || '3031', 10);
const WS_PORT = parseInt(process.env.OVERTURE_WS_PORT     || '3030', 10);

// --- HTTP proxy -----------------------------------------------------------

const server = http.createServer((req, res) => {
  const opts = {
    host:    '127.0.0.1',
    port:    UI_PORT,
    path:    req.url,
    method:  req.method,
    headers: { ...req.headers, host: `127.0.0.1:${UI_PORT}` },
  };

  const proxyReq = http.request(opts, (proxyRes) => {
    const ct = proxyRes.headers['content-type'] || '';

    if (ct.includes('javascript')) {
      // Buffer the JS, patch the hardcoded WS URL, forward
      const chunks = [];
      proxyRes.on('data', (c) => chunks.push(c));
      proxyRes.on('end', () => {
        let body = Buffer.concat(chunks).toString('utf8');

        // Replace the literal constant with a runtime expression.
        // The minified bundle uses:  jw="ws://localhost:3030"
        body = body.replaceAll(
          '"ws://localhost:3030"',
          '"ws://"+location.hostname+":3030"',
        );

        const headers = { ...proxyRes.headers };
        delete headers['content-encoding'];   // we decoded it already
        headers['content-length'] = Buffer.byteLength(body, 'utf8').toString();

        res.writeHead(proxyRes.statusCode ?? 200, headers);
        res.end(body);
      });
    } else {
      // Pass through everything else unchanged
      res.writeHead(proxyRes.statusCode ?? 200, proxyRes.headers);
      proxyRes.pipe(res);
    }
  });

  proxyReq.on('error', (err) => {
    if (!res.headersSent) {
      res.writeHead(502, { 'content-type': 'text/plain' });
      res.end(
        `Overture UI not available on port ${UI_PORT}.\n` +
        `Make sure overture-mcp is running (registered with Claude Code).\n\n` +
        err.message,
      );
    }
  });

  req.pipe(proxyReq);
});

// --- WebSocket proxy ------------------------------------------------------

server.on('upgrade', (req, clientSocket, head) => {
  clientSocket.on('error', () => {});   // swallow broken-pipe errors

  const serverSocket = net.connect(WS_PORT, '127.0.0.1', () => {
    // Re-send the original HTTP upgrade request to the WS server
    const headerLines = Object.entries(req.headers)
      .map(([k, v]) => `${k}: ${v}`)
      .join('\r\n');

    serverSocket.write(
      `GET ${req.url ?? '/'} HTTP/1.1\r\n${headerLines}\r\n\r\n`,
    );
    if (head && head.length > 0) serverSocket.write(head);

    clientSocket.pipe(serverSocket);
    serverSocket.pipe(clientSocket);
  });

  serverSocket.on('error', () => clientSocket.destroy());
  clientSocket.on('close', () => serverSocket.destroy());
  serverSocket.on('close', () => clientSocket.destroy());
});

// --- Start ----------------------------------------------------------------

server.listen(PORT, '0.0.0.0', () => {
  // Detect Tailscale IP from env or use known value
  const tsIP = process.env.TAILSCALE_IP || '100.125.138.97';

  console.log('[overture-proxy] Remote access proxy started');
  console.log(`  Localhost:  http://localhost:${PORT}`);
  console.log(`  LAN:        http://192.168.86.25:${PORT}`);
  console.log(`  Tailscale:  http://${tsIP}:${PORT}`);
  console.log('');
  console.log('Open the Tailscale URL on your phone or another computer.');
});
