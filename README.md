# Codex Favourite Skills

A curated collection of reusable skills that make Codex more rigorous, reliable, and useful.

## Skills

| Skill | Purpose |
| --- | --- |
| [`challenge-assumptions`](skills/challenge-assumptions/) | Keep investigations evidence-led by testing plausible explanations before treating them as root causes. |

## Install a skill

Copy the skill folder into your user skills directory:

```text
$HOME/.agents/skills/
```

For example, after cloning this repository on macOS or Linux:

```bash
mkdir -p "$HOME/.agents/skills"
cp -R skills/challenge-assumptions "$HOME/.agents/skills/"
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse -Force "skills\challenge-assumptions" "$HOME\.agents\skills\"
```

Codex detects skill changes automatically. Restart Codex if the skill does not appear.

## Use a skill

Invoke a skill explicitly in a prompt by mentioning it with `$`, for example:

```text
Use $challenge-assumptions to investigate why this repair did not change the observed behavior.
```

Codex can also select a skill automatically when the request matches the skill description.

## License

MIT. See [LICENSE](LICENSE).
