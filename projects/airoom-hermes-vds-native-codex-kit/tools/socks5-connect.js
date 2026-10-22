const net = require("net");

const [host, portText, proxyHost = "127.0.0.1", proxyPortText = "7897"] = process.argv.slice(2);
if (!host || !portText) {
  console.error("Usage: node socks5-connect.js <host> <port> [proxyHost] [proxyPort]");
  process.exit(2);
}

const port = Number(portText);
const proxyPort = Number(proxyPortText);
const socket = net.connect(proxyPort, proxyHost);

function readExact(size) {
  return new Promise((resolve, reject) => {
    let chunks = [];
    let length = 0;

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
      reject(new Error("SOCKS proxy closed connection"));
    }

    function onData(chunk) {
      chunks.push(chunk);
      length += chunk.length;
      if (length < size) return;

      cleanup();
      const buffer = Buffer.concat(chunks, length);
      const needed = buffer.subarray(0, size);
      const rest = buffer.subarray(size);
      if (rest.length) socket.unshift(rest);
      resolve(needed);
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

  socket.write(Buffer.from([0x05, 0x01, 0x00]));
  const hello = await readExact(2);
  if (hello[0] !== 0x05 || hello[1] !== 0x00) {
    throw new Error("SOCKS proxy refused no-auth connection");
  }

  const hostBytes = Buffer.from(host, "ascii");
  if (hostBytes.length > 255) throw new Error("Host name is too long for SOCKS5");

  socket.write(Buffer.concat([
    Buffer.from([0x05, 0x01, 0x00, 0x03, hostBytes.length]),
    hostBytes,
    Buffer.from([(port >> 8) & 0xff, port & 0xff]),
  ]));

  const reply = await readExact(4);
  if (reply[1] !== 0x00) throw new Error(`SOCKS connect failed with code 0x${reply[1].toString(16)}`);

  if (reply[3] === 0x01) await readExact(4);
  else if (reply[3] === 0x03) await readExact((await readExact(1))[0]);
  else if (reply[3] === 0x04) await readExact(16);
  else throw new Error("SOCKS proxy returned unknown address type");
  await readExact(2);

  process.stdin.pipe(socket);
  socket.pipe(process.stdout);
  socket.on("close", () => process.exit(0));
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
