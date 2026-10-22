# Скрипт автоматического обновления списка серверов Browsec VPN в профиле Clash Verge
# 1. Запрашивает актуальный пул серверов из API расширения Browsec
# 2. Обновляет D:\AI\Antigravity\Browsec-Clash-Verge.yaml
# 3. Синхронизирует импортированный профиль внутри Clash Verge (%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\profiles)
# 4. Если профиль активен — обновляет рантайм-конфиг clash-verge.yaml и выполняет hot-reload ядра Mihomo через Named Pipe

param(
    [string]$OutputPath = "D:\AI\Antigravity\Browsec-Clash-Verge.yaml"
)

$ErrorActionPreference = "Stop"

$apiUrls = @(
    "https://e4.bmtr.org/api/v1/servers?stdomains=1&cid=00000000-0000-4000-8000-000000000000",
    "https://e5.bmtr.org/api/v1/servers?stdomains=1&cid=00000000-0000-4000-8000-000000000000",
    "https://dikpnngjfcoep.cloudfront.net/v1/servers?stdomains=1&cid=00000000-0000-4000-8000-000000000000"
)

$data = $null
foreach ($url in $apiUrls) {
    try {
        $raw = curl.exe -s -m 10 $url
        if ($raw) {
            $parsed = $raw | ConvertFrom-Json
            if ($parsed.countries) {
                $data = $parsed
                Write-Host "Получен список серверов Browsec (version: $($data.version)) с $url"
                break
            }
        }
    } catch {
        continue
    }
}

if (-not $data) {
    throw "Не удалось получить список серверов ни с одного зеркала API Browsec."
}

$countryMeta = [ordered]@{
    "nl" = @{ Flag = "🇳🇱"; Title = "Netherlands" }
    "de" = @{ Flag = "🇩🇪"; Title = "Germany" }
    "lt" = @{ Flag = "🇱🇹"; Title = "Lithuania" }
    "lv" = @{ Flag = "🇱🇻"; Title = "Latvia" }
    "uk" = @{ Flag = "🇬🇧"; Title = "United Kingdom" }
    "us" = @{ Flag = "🇺🇸"; Title = "United States" }
    "sg" = @{ Flag = "🇸🇬"; Title = "Singapore" }
}

$proxiesYaml = [System.Collections.Generic.List[string]]::new()
$allProxyNames = [System.Collections.Generic.List[string]]::new()
$countryGroupsYaml = [System.Collections.Generic.List[string]]::new()
$countryGroupNames = [System.Collections.Generic.List[string]]::new()

foreach ($code in $countryMeta.Keys) {
    $countryObj = $data.countries.$code
    if (-not $countryObj -or -not $countryObj.servers) { continue }

    $meta = $countryMeta[$code]
    $groupName = "$($meta.Flag) $($meta.Title)"
    $countryGroupNames.Add($groupName)
    $thisCountryProxies = [System.Collections.Generic.List[string]]::new()

    $idx = 1
    foreach ($srv in $countryObj.servers) {
        $upper = $code.ToUpper()
        $proxyName = "$($meta.Flag) $upper-$idx ($($srv.host))"
        $allProxyNames.Add($proxyName)
        $thisCountryProxies.Add($proxyName)

        $proxiesYaml.Add("  - name: `"$proxyName`"")
        $proxiesYaml.Add("    type: http")
        $proxiesYaml.Add("    server: $($srv.host)")
        $proxiesYaml.Add("    port: $($srv.port)")
        $proxiesYaml.Add("    tls: true")
        $proxiesYaml.Add("    sni: $($srv.host)")
        $proxiesYaml.Add("    skip-cert-verify: false")
        $proxiesYaml.Add("")
        $idx++
    }

    $countryGroupsYaml.Add("  - name: `"$groupName`"")
    $countryGroupsYaml.Add("    type: url-test")
    $countryGroupsYaml.Add("    url: `"https://www.gstatic.com/generate_204`"")
    $countryGroupsYaml.Add("    interval: 300")
    $countryGroupsYaml.Add("    proxies:")
    foreach ($pName in $thisCountryProxies) {
        $countryGroupsYaml.Add("      - `"$pName`"")
    }
    $countryGroupsYaml.Add("")
}

$bodySb = [System.Text.StringBuilder]::new()
[void]$bodySb.AppendLine("proxies:")
foreach ($line in $proxiesYaml) { [void]$bodySb.AppendLine($line) }

[void]$bodySb.AppendLine("proxy-groups:")
[void]$bodySb.AppendLine("  - name: `"PROXY`"")
[void]$bodySb.AppendLine("    type: select")
[void]$bodySb.AppendLine("    proxies:")
[void]$bodySb.AppendLine("      - `"⚡ AUTO (Fastest)`"")
foreach ($gName in $countryGroupNames) { [void]$bodySb.AppendLine("      - `"$gName`"") }
[void]$bodySb.AppendLine("      - DIRECT")
[void]$bodySb.AppendLine("")
[void]$bodySb.AppendLine("  - name: `"⚡ AUTO (Fastest)`"")
[void]$bodySb.AppendLine("    type: url-test")
[void]$bodySb.AppendLine("    url: `"https://www.gstatic.com/generate_204`"")
[void]$bodySb.AppendLine("    interval: 300")
[void]$bodySb.AppendLine("    tolerance: 50")
[void]$bodySb.AppendLine("    proxies:")
foreach ($pName in $allProxyNames) { [void]$bodySb.AppendLine("      - `"$pName`"") }
[void]$bodySb.AppendLine("")
foreach ($line in $countryGroupsYaml) { [void]$bodySb.AppendLine($line) }

$rulesBlock = @"
rules:
  # 1. Local & Private Networks -> DIRECT (аналогично ipRanges в PAC-скрипте Browsec)
  - DOMAIN-SUFFIX,local,DIRECT
  - IP-CIDR,127.0.0.0/8,DIRECT
  - IP-CIDR,10.0.0.0/8,DIRECT
  - IP-CIDR,172.16.0.0/12,DIRECT
  - IP-CIDR,192.168.0.0/16,DIRECT
  - IP-CIDR,100.64.0.0/10,DIRECT
  - IP-CIDR6,::1/128,DIRECT
  - IP-CIDR6,fc00::/7,DIRECT
  - IP-CIDR6,fe80::/10,DIRECT

  # 2. Telegram Explicit Proxy Rules
  - DOMAIN-SUFFIX,telegram.org,PROXY
  - DOMAIN-SUFFIX,t.me,PROXY
  - DOMAIN-SUFFIX,tdesktop.com,PROXY
  - DOMAIN-SUFFIX,telegra.ph,PROXY
  - DOMAIN-KEYWORD,telegram,PROXY
  - IP-CIDR,91.108.4.0/22,PROXY,no-resolve
  - IP-CIDR,91.108.8.0/22,PROXY,no-resolve
  - IP-CIDR,91.108.12.0/22,PROXY,no-resolve
  - IP-CIDR,91.108.16.0/22,PROXY,no-resolve
  - IP-CIDR,91.108.56.0/22,PROXY,no-resolve
  - IP-CIDR,149.154.160.0/20,PROXY,no-resolve

  # 3. Instagram & Meta Explicit Proxy Rules
  - DOMAIN-SUFFIX,instagram.com,PROXY
  - DOMAIN-SUFFIX,cdninstagram.com,PROXY
  - DOMAIN-SUFFIX,facebook.com,PROXY
  - DOMAIN-SUFFIX,fbcdn.net,PROXY
  - DOMAIN-KEYWORD,instagram,PROXY

  # 4. YouTube & Google Video Proxy Rules
  - DOMAIN-SUFFIX,youtube.com,PROXY
  - DOMAIN-SUFFIX,googlevideo.com,PROXY
  - DOMAIN-SUFFIX,ytimg.com,PROXY
  - DOMAIN-SUFFIX,youtu.be,PROXY

  # 5. Russian Services on non-RU domains -> DIRECT (аналогично RUSSIAN_EXTRA_DOMAINS в Browsec)
  - DOMAIN-SUFFIX,yandex.com,DIRECT
  - DOMAIN-SUFFIX,yandex.net,DIRECT
  - DOMAIN-SUFFIX,yastatic.net,DIRECT
  - DOMAIN-SUFFIX,kinopoisk-ott.me,DIRECT
  - DOMAIN-SUFFIX,kpcdn.net,DIRECT
  - DOMAIN-SUFFIX,vk.com,DIRECT
  - DOMAIN-SUFFIX,vk.me,DIRECT
  - DOMAIN-SUFFIX,vkuser.net,DIRECT
  - DOMAIN-SUFFIX,mycdn.me,DIRECT
  - DOMAIN-SUFFIX,userapi.com,DIRECT
  - DOMAIN-SUFFIX,dzen.ru,DIRECT
  - DOMAIN-SUFFIX,tinkoff.com,DIRECT
  - DOMAIN-SUFFIX,t-bank.com,DIRECT
  - DOMAIN-SUFFIX,tbank.me,DIRECT
  - DOMAIN-SUFFIX,sberbank.com,DIRECT
  - DOMAIN-SUFFIX,sber.me,DIRECT
  - DOMAIN-SUFFIX,alfabank.com,DIRECT
  - DOMAIN-SUFFIX,vtb.com,DIRECT
  - DOMAIN-SUFFIX,tochka.com,DIRECT
  - DOMAIN-SUFFIX,modulbank.com,DIRECT
  - DOMAIN-SUFFIX,ozon.com,DIRECT
  - DOMAIN-SUFFIX,ozon.travel,DIRECT
  - DOMAIN-SUFFIX,wildberries.com,DIRECT
  - DOMAIN-SUFFIX,wb.me,DIRECT
  - DOMAIN-SUFFIX,avito.st,DIRECT
  - DOMAIN-SUFFIX,cdek.com,DIRECT
  - DOMAIN-SUFFIX,lamoda.com,DIRECT
  - DOMAIN-SUFFIX,vseinstrumenti.tech,DIRECT
  - DOMAIN-SUFFIX,megamarket.tech,DIRECT
  - DOMAIN-SUFFIX,habr.com,DIRECT
  - DOMAIN-SUFFIX,pikabu.com,DIRECT
  - DOMAIN-SUFFIX,2gis.com,DIRECT
  - DOMAIN-SUFFIX,hh.com,DIRECT
  - DOMAIN-SUFFIX,ivi.tv,DIRECT
  - DOMAIN-SUFFIX,okko.tv,DIRECT
  - DOMAIN-SUFFIX,premier.one,DIRECT

  # 6. Russian National Domains -> DIRECT (аналогично RUSSIAN_TLDS в Browsec)
  - DOMAIN-SUFFIX,ru,DIRECT
  - DOMAIN-SUFFIX,su,DIRECT
  - DOMAIN-SUFFIX,tatar,DIRECT
  - DOMAIN-SUFFIX,moscow,DIRECT
  - DOMAIN-SUFFIX,xn--p1ai,DIRECT
  - DOMAIN-SUFFIX,xn--80adxhks,DIRECT
  - DOMAIN-SUFFIX,xn--d1acj3b,DIRECT
  - DOMAIN-SUFFIX,xn--p1acf,DIRECT
  - DOMAIN-SUFFIX,рф,DIRECT
  - DOMAIN-SUFFIX,ya.ru,DIRECT
  - DOMAIN-SUFFIX,yandex.ru,DIRECT
  - DOMAIN-SUFFIX,avito.ru,DIRECT
  - DOMAIN-SUFFIX,ozon.ru,DIRECT
  - DOMAIN-SUFFIX,wildberries.ru,DIRECT
  - DOMAIN-SUFFIX,gosuslugi.ru,DIRECT
  - DOMAIN-SUFFIX,sberbank.ru,DIRECT
  - DOMAIN-SUFFIX,sber.ru,DIRECT
  - DOMAIN-SUFFIX,tbank.ru,DIRECT
  - DOMAIN-SUFFIX,tinkoff.ru,DIRECT
  - DOMAIN-SUFFIX,vtb.ru,DIRECT
  - DOMAIN-SUFFIX,vk.ru,DIRECT
  - DOMAIN-SUFFIX,mail.ru,DIRECT
  - DOMAIN-SUFFIX,ok.ru,DIRECT
  - DOMAIN-SUFFIX,rutube.ru,DIRECT

  # 7. GeoIP Russia -> DIRECT
  - GEOIP,RU,DIRECT

  # 8. All other traffic -> PROXY
  - MATCH,PROXY
"@
[void]$bodySb.AppendLine($rulesBlock)
$proxiesAndRulesText = $bodySb.ToString()

$headerSb = [System.Text.StringBuilder]::new()
[void]$headerSb.AppendLine("# Clash Verge Rev / Mihomo Profile — Browsec VPN (version: $($data.version))")
[void]$headerSb.AppendLine("mixed-port: 7897")
[void]$headerSb.AppendLine("allow-lan: false")
[void]$headerSb.AppendLine("mode: rule")
[void]$headerSb.AppendLine("log-level: info")
[void]$headerSb.AppendLine("ipv6: false")
[void]$headerSb.AppendLine("")
[void]$headerSb.AppendLine("profile:")
[void]$headerSb.AppendLine("  store-selected: true")
[void]$headerSb.AppendLine("  store-fake-ip: false")
[void]$headerSb.AppendLine("")
[void]$headerSb.AppendLine("tun:")
[void]$headerSb.AppendLine("  enable: false")
[void]$headerSb.AppendLine("")
[void]$headerSb.AppendLine("sniffer:")
[void]$headerSb.AppendLine("  enable: true")
[void]$headerSb.AppendLine("  sniff:")
[void]$headerSb.AppendLine("    TLS:")
[void]$headerSb.AppendLine("      ports: [443, 8443]")
[void]$headerSb.AppendLine("    HTTP:")
[void]$headerSb.AppendLine("      ports: [80, 8080-8880]")
[void]$headerSb.AppendLine("      override-destination: true")
[void]$headerSb.AppendLine("")
[void]$headerSb.AppendLine("dns:")
[void]$headerSb.AppendLine("  enable: false")
[void]$headerSb.AppendLine("")

$fullProfileText = $headerSb.ToString() + $proxiesAndRulesText
Set-Content -LiteralPath $OutputPath -Value $fullProfileText -Encoding UTF8
Write-Host "Локальный файл профиля обновлён: $OutputPath ($($allProxyNames.Count) прокси-нод)"

# Синхронизация с импортированным профилем в Clash Verge
$cvDir = "$env:APPDATA\io.github.clash-verge-rev.clash-verge-rev"
$profilesMetaPath = Join-Path $cvDir "profiles.yaml"
if (Test-Path -LiteralPath $profilesMetaPath) {
    $profilesMetaText = Get-Content -LiteralPath $profilesMetaPath -Raw
    $currentMatch = [regex]::Match($profilesMetaText, '(?m)^current:\s*(\S+)')
    $currentUid = if ($currentMatch.Success) { $currentMatch.Groups[1].Value } else { "" }

    $uidMatches = [regex]::Matches($profilesMetaText, '(?ms)-\s*uid:\s*(\S+)\s+type:\s*local\s+name:\s*Browsec-Clash-Verge\.yaml\s+file:\s*(\S+)')
    foreach ($m in $uidMatches) {
        $uid = $m.Groups[1].Value
        $fileName = $m.Groups[2].Value
        $targetProfileFile = Join-Path (Join-Path $cvDir "profiles") $fileName
        if (Test-Path -LiteralPath $targetProfileFile) {
            Set-Content -LiteralPath $targetProfileFile -Value $fullProfileText -Encoding UTF8
            Write-Host "Обновлён внутренний профиль Clash Verge: $targetProfileFile (uid: $uid)"
        }

        if ($uid -eq $currentUid) {
            $runtimeConfigPath = Join-Path $cvDir "clash-verge.yaml"
            if (Test-Path -LiteralPath $runtimeConfigPath) {
                $runtimeText = Get-Content -LiteralPath $runtimeConfigPath -Raw
                $proxiesIdx = $runtimeText.IndexOf("`nproxies:")
                if ($proxiesIdx -ge 0) {
                    $runtimeHeader = $runtimeText.Substring(0, $proxiesIdx + 1)
                    $newRuntimeText = $runtimeHeader + $proxiesAndRulesText
                    Set-Content -LiteralPath $runtimeConfigPath -Value $newRuntimeText -Encoding UTF8
                    Write-Host "Обновлён активный рантайм-конфиг: $runtimeConfigPath"

                    # Hot-reload ядра Mihomo через Named Pipe
                    $pipeItem = Get-ChildItem -LiteralPath "\\.\pipe\" -ErrorAction SilentlyContinue |
                        Where-Object { $_.Name -like "verge-mihomo*" } |
                        Select-Object -First 1
                    if ($pipeItem) {
                        $pipe = [System.IO.Pipes.NamedPipeClientStream]::new(".", $pipeItem.Name, [System.IO.Pipes.PipeDirection]::InOut)
                        try {
                            $pipe.Connect(2000)
                            $jsonBody = (@{ payload = $newRuntimeText } | ConvertTo-Json -Compress)
                            $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($jsonBody)
                            $reqHeader = "PUT /configs?force=true HTTP/1.1`r`nHost: localhost`r`nContent-Type: application/json`r`nContent-Length: $($bodyBytes.Length)`r`nConnection: close`r`n`r`n"
                            $headerBytes = [System.Text.Encoding]::ASCII.GetBytes($reqHeader)
                            $pipe.Write($headerBytes, 0, $headerBytes.Length)
                            $pipe.Write($bodyBytes, 0, $bodyBytes.Length)
                            $pipe.Flush()
                            $sr = [System.IO.StreamReader]::new($pipe)
                            $resp = $sr.ReadToEnd()
                            $statusLine = ($resp -split "`r?`n")[0]
                            Write-Host "Mihomo hot-reload: $statusLine"
                        } finally {
                            $pipe.Dispose()
                        }
                    }
                }
            }
        }
    }
}
