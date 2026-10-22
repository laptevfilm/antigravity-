param(
  [Parameter(Mandatory=$true)][string]$HostName,
  [Parameter(Mandatory=$true)][int]$Port,
  [string]$ProxyHost = "127.0.0.1",
  [int]$ProxyPort = 7898
)

$client = [System.Net.Sockets.TcpClient]::new()
$client.Connect($ProxyHost, $ProxyPort)
$stream = $client.GetStream()

function Write-Bytes([byte[]]$bytes) {
  $stream.Write($bytes, 0, $bytes.Length)
  $stream.Flush()
}

function Read-Exact([int]$count) {
  $buffer = [byte[]]::new($count)
  $offset = 0
  while ($offset -lt $count) {
    $read = $stream.Read($buffer, $offset, $count - $offset)
    if ($read -le 0) { throw "SOCKS proxy closed connection" }
    $offset += $read
  }
  return $buffer
}

Write-Bytes ([byte[]](0x05, 0x01, 0x00))
$hello = Read-Exact 2
if ($hello[0] -ne 0x05 -or $hello[1] -ne 0x00) {
  throw "SOCKS proxy refused no-auth connection"
}

$hostBytes = [System.Text.Encoding]::ASCII.GetBytes($HostName)
if ($hostBytes.Length -gt 255) { throw "Host name is too long for SOCKS5" }
$portBytes = [byte[]]((($Port -shr 8) -band 0xff), ($Port -band 0xff))
Write-Bytes ([byte[]](0x05, 0x01, 0x00, 0x03, $hostBytes.Length) + $hostBytes + $portBytes)

$reply = Read-Exact 4
if ($reply[1] -ne 0x00) { throw ("SOCKS connect failed with code 0x{0:X2}" -f $reply[1]) }

switch ($reply[3]) {
  0x01 { [void](Read-Exact 4) }
  0x03 { $len = (Read-Exact 1)[0]; [void](Read-Exact $len) }
  0x04 { [void](Read-Exact 16) }
  default { throw "SOCKS proxy returned unknown address type" }
}
[void](Read-Exact 2)

$stdin = [Console]::OpenStandardInput()
$stdout = [Console]::OpenStandardOutput()
$closed = $false

$toProxy = [System.Threading.Thread]::new({
  $buf = [byte[]]::new(32768)
  try {
    while (-not $script:closed) {
      $n = $script:stdin.Read($buf, 0, $buf.Length)
      if ($n -le 0) { break }
      $script:stream.Write($buf, 0, $n)
      $script:stream.Flush()
    }
  } finally {
    $script:closed = $true
    try { $script:client.Close() } catch {}
  }
})

$fromProxy = [System.Threading.Thread]::new({
  $buf = [byte[]]::new(32768)
  try {
    while (-not $script:closed) {
      $n = $script:stream.Read($buf, 0, $buf.Length)
      if ($n -le 0) { break }
      $script:stdout.Write($buf, 0, $n)
      $script:stdout.Flush()
    }
  } finally {
    $script:closed = $true
    try { $script:client.Close() } catch {}
  }
})

$toProxy.Start()
$fromProxy.Start()
$toProxy.Join()
$fromProxy.Join()
$client.Close()
