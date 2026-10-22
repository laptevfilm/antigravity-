const net = require("net");

const [host, portText, proxyHost = "127.0.0.1", proxyPortText = "7897"] = process.argv.slice(2);
if (!host || !portText) {
  console.error("Usage: node http-connect.js <host> <port> [proxyHost] [proxyPort]");
  process.exit(2);
}

const port = Number(portText);
const proxyPort = Number(proxyPortText);
const socket = net.connect(proxyPort, proxyHost);

let buffer = Buffer.alloc(0);

function waitForHeaders() {
  return new Promise((resolve, reject) => {
    function cleanup() {
      socket.off("data", onData);
      socket.off("error", onError);
      socket.off("end", onEnd);
    }

    function onError(error) {
      cleanup();
      reject(error);
    }

    function onEnd() {
      cleanup();
      reject(new Error("HTTP proxy closed connection"));
    }

    function onData(chunk) {
      buffer = Buffer.concat([buffer, chunk]);
      const headerEnd = buffer.indexOf("\r\n\r\n");
      if (headerEnd === -1) return;

      cleanup();
      const headers = buffer.subarray(0, headerEnd).toString("latin1");
      const rest = buffer.subarray(headerEnd + 4);
      resolve({ headers, rest });
    }

    socket.on("data", onData);
    socket.once("error", onError);
    socket.once("end", onEnd);
  });
}

async function main() {
  await new Promise((resolve, reject) => {
    socket.once("connect", resolve);
    socket.once("error", reject);
  });

  socket.write(`CONNECT ${host}:${port} HTTP/1.1\r\nHost: ${host}:${port}\r\nProxy-Connection: Keep-Alive\r\n\r\n`);
  const { headers, rest } = await waitForHeaders();
  if (!/^HTTP\/1\.[01] 2\d\d\b/.test(headers)) {
    throw new Error(headers.split(/\r?\n/)[0] || "HTTP CONNECT failed");
  }

  if (rest.length) process.stdout.write(rest);
  process.stdin.pipe(socket);
  socket.pipe(process.stdout);
  socket.on("close", () => process.exit(0));
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
