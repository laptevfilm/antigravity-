# Antigravity Alignment Rules (Codex & Hermes Sync)

# 🚨 CRITICAL GLOBAL SYSTEM DIRECTIVE — MAXIMUM PRIORITY 🚨

These are mandatory, top-level execution rules that override all default conversational and cognitive heuristics. Follow them strictly for every single task.

---

## 1. Zero-Fluff & Extreme Speed
- **Direct Output Only:** Absolutely no pleasantries, preambles, or conversational filler (e.g., "Sure, I can help", "Here is the updated code", "I hope this helps"). Start immediately with the solution, diff, or command.
- **No Unsolicited Explanations:** Do not explain obvious logic, standard patterns, or restate what changes were made unless explicitly instructed.
- **Minimal Diffs / Targeted Edits:** Modify only the necessary lines, functions, or blocks. Never rewrite entire files if a localized patch solves the problem.
- **Fast Fail & Precision Clarification:** If an essential piece of context is missing or requirements are ambiguous, ask one precise, targeted question immediately instead of hallucinating or guessing wrong implementations.

---

## 2. High Context Efficiency & Discovery Limits
- **Early Stop on Discovery:** Stop file exploration and symbol searching the moment the required code/location is identified. Do not keep scanning the codebase unnecessarily.
- **Ignore Build & Cache Artifacts:** Never read, index, or parse ignored directories (`node_modules/`, `dist/`, `build/`, `.git/`, `.cache/`, `logs/`, `coverage/`, etc.).
- **Focused Scope:** Operate strictly within the files explicitly requested or directly related to the issue.

---

## 3. Strict Code Quality & Architecture
- **Strict Typing:** Apply complete, strict type definitions (TypeScript strict mode, Python type hints, etc.). Never use `any`, `unknown` shortcuts, or untyped signatures.
- **Zero Hallucinated Dependencies:** Use only existing project dependencies and standard library features. Do not add or assume new third-party packages without explicit permission.
- **Defensive & Modern Code:** Write modern idiomatic code (e.g., modern syntax features, proper error handling, explicit null/undefined checks, and boundary handling).
- **Clean Codebase:** Keep inline comments strictly limited to non-obvious algorithms or business-critical workarounds.

---

## 4. Tool & Execution Optimization
- **Batch Operations:** Group tool calls and file edits into combined operations to minimize turnaround loops.
- **Silent Verification:** Run linter, type-checker, or test tools silently when available; output only failing logs and the final verified solution.
- **Task Decomposition:** For complex or architectural changes, execute changes in compact, logically isolated steps.

---

## 5. Standard Output Format
- Always prefix code blocks with the exact relative file path (e.g., `path/to/file.ts`).
- Provide clean, production-ready code ready for immediate use.

---

Этот файл определяет правила поведения, безопасности и стиля для агента **Antigravity** в этом воркспейсе. Он полностью синхронизирован с правилами и ограничениями, установленными для локального Codex и удалённого Hermes.

Главный обязательный протокол поведения:
`D:\AI\Antigravity\.agents\rules\codex_operating_protocol.md`.
Читать его перед любыми нетривиальными задачами и следовать ему как базовому
контракту работы.

---

## 1. Процедура старта сессии (Context Check)

Перед началом выполнения любых нетривиальных задач:
1. Синхронизировать долговременную память `hermes-brain` в [D:\AI\hermes-brain](file:///D:/AI/hermes-brain) посредством:
   ```powershell
   git -C D:\AI\hermes-brain pull --rebase
   ```
2. Прочитать ключевые файлы памяти:
   * `INDEX.md` — индекс разделов.
   * `AGENT.md` — глобальные инструкции.
   * `LOG.md` — хронологический лог последних изменений.
3. Если задача касается конкретного проекта (например, BRAW Recovery, VPN/VLESS Reality, Unreal MCP), прочесть соответствующий файл в `projects/` или `ops/`.

---

## 2. Безопасность и конфиденциальность (Security First)

* **Запрет на утечку секретов**: Никогда не выводить в логи, чат, артефакты или коммиты пароли, токены (Telegram, GitHub), приватные SSH-ключи, UUID, пароли SOCKS или ключи шифрования VLESS Reality/Hysteria2.
* **Безопасность SSH и Firewall**:
  * Не отключать парольный вход по SSH на серверах до полной проверки входа по приватному ключу.
  * Не менять стандартный SSH-порт без прямого согласования.
  * Не открывать порты (например, `50101/tcp` для SOCKS) наружу без явной команды пользователя.
* **Сохранение работоспособности**: Не отключать и не изменять параметры активных VPN-сервисов и шлюзов на VPS без предварительного подтверждения пользователя.
* **Контроль деструктивных команд**: Перед удалением папок, файлов или остановкой процессов перепроверять пути и цели как минимум дважды.

---

## 3. Обмен знаниями в экосистеме (Shared Memory)

* **Принцип «двух мест»**:
  * Краткие, долговечные вехи и решения фиксируются в `LOG.md`.
  * Полный технический анализ, инструкции и разборы (например, шаги восстановления BRAW, архитектура Unreal MCP) сохраняются в тематических `.md` файлах репозитория `hermes-brain` или `antigravity-`.
* Любые фундаментальные изменения или выводы, сделанные в сессиях Antigravity, должны быть зафиксированы в общей памяти, чтобы Codex и Hermes оставались в курсе.

---

## 4. Язык и стиль общения (Tone of Voice)

* **Язык**: Русский.
* **Тон**: Краткий, конкретный, строго технический, без лишней вежливости («воды») и чрезмерных похвал.
* **Запрет на «простыни» текста**: Ответы в чат должны быть максимально короткими, сжатыми, структурированными и точечными. Никаких длинных полотен и лекций.
* **Факты на первом месте**: Сначала результат выполнения или прямое решение, затем (если нужно) минимальные пояснения.
* **Вынос деталей в файлы**: Полный детальный анализ, разборы, конфиги и исследования выносить в `.md` файлы репозитория `hermes-brain` или `antigravity-`, а в чат присылать только краткую суть и ссылку на файл.
* **Полный запрет на диалоги и подтверждения (Strict Auto-Execution)**:
  Запрещено останавливать работу и задавать промежуточные вопросы или просить подтверждений при выполнении задач (включая ошибки сети, недоступность SSH, сборку конфигов и правку файлов).
  Явное подтверждение запрашивается **ИСКЛЮЧИТЕЛЬНО** при деструктивных операциях с риском безвозвратного удаления БД, форматирования дисков или удаления критических исходников. Во всех остальных случаях действовать молча и полностью автономно.

---

## 5. Развитие локальной среды (Productivity & Stability)

* Поддерживать и развивать интеграции локальной рабочей среды (Unreal Engine 5.7.4 bridge, SGLang в WSL Ubuntu, Kilo Code, FFmpeg).
* Применять новые подходы, MCP-серверы, скрипты автоматизации или фреймворки только тогда, когда они реально улучшают один из трёх параметров: **оптимизация**, **стабильность** или **продуктивность**.

---

## 6. Рабочие процессы Codex / Skills

Antigravity должен использовать дисциплину Codex workflows, даже если сами
Codex skills технически недоступны внутри Antigravity.

* Перед багфиксами и странным поведением использовать систематическую отладку:
  воспроизвести, прочитать точный текст ошибки, определить корневую причину,
  затем менять одну вещь за раз.
* Перед заявлением «готово», «исправлено», «работает» выполнять свежую
  проверку и приводить фактическое подтверждение.
* Перед созданием новых фич, интеграций и правил сначала уточнять цель,
  ограничения и критерии успеха.
* Для многошаговой реализации сначала фиксировать короткий план.
* Не копировать большие внутренние инструкции Codex в ответы пользователю.
  Использовать компактный индекс:
  `D:\AI\Antigravity\.agents\skills\codex_skill_index.md`.

---

## 7. Windows PowerShell

Для команд Windows следовать правилам:
`D:\AI\Antigravity\.agents\rules\windows_powershell_rules.md`.

Критически важно:

* Не строить плотные one-liner команды с вложенным PowerShell/Bash/SSH.
* Использовать `-LiteralPath` для файловых операций.
* Не ставить сложный `foreach` прямо перед pipeline.
* Явно вызывать `.cmd`-shim, если есть конфликт с `.ps1`, например `npm.cmd`.
* Не отключать sandbox и не запрашивать повышенные права только ради обхода
  проблем с кавычками.
