# Windows PowerShell Rules

These rules are mandatory for Antigravity when working on this Windows machine.
They mirror the local Codex rules and prevent repeated failures with quoting,
UTF-8, sandboxed execution, and nested shell commands.

## Command Style

- Prefer simple PowerShell commands over dense one-liners.
- If a command needs multiple logical steps, split it into separate commands or
  assign intermediate results to variables.
- Do not place a complex `foreach` block directly before a pipeline. Use:

  ```powershell
  $results = foreach ($item in $items) {
      # action
  }
  $results | Format-Table
  ```

## Paths and Files

- Pass paths as separate arguments.
- Prefer `-LiteralPath` for user paths, spaces, brackets, and non-ASCII names.
- Before recursive delete or move, resolve and verify the absolute target path.
- Never delete outside the intended workspace.

## External Programs

- When a tool may have both `.ps1` and `.cmd` shims, call the intended command
  explicitly, for example `npm.cmd`.
- For Python checks, prefer the configured local tools:
  `D:\AI\Tools\Python\3.12.10`.
- Expected sandbox-safe PowerShell:
  `D:\AI\Tools\PowerShell\7.6.3\pwsh.exe`.

## SSH and Nested Shells

- Avoid nested quoting such as `ssh "... bash -lc '...'"`.
- Prefer simple remote commands, a temporary script, or separate calls.
- Do not hide quoting problems by disabling sandboxing or escalating privileges.
  Escalate only when the action genuinely needs network, GUI, system rights, or
  access outside writable roots.

## Diagnostics

If sandbox or shell startup errors return, inspect:

- `C:\Users\Gray\.codex\.sandbox\sandbox.YYYY-MM-DD.log`
- `D:\AI\hermes-brain\ops\codex-windows-sandbox.md`

