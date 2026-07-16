# Evergreen Codex Skills

Durable, generally useful Codex skills designed to stay valuable as models improve.

## Install

Paste this repository link into Codex and say **“Install from this repo.”**

```text
https://github.com/Kbediako/evergreen-codex-skills
```

That is enough. Codex can install the only available skill directly. As the
[catalogue](skills/README.md) grows, it should show you the choices unless you
name a skill or ask to install them all.

### For Codex

When asked to install from this repository, read `skills/README.md`. If one
skill is available, install it; if several are available and the user did not
choose, present the catalogue first. Use `$skill-installer` with each selected
`skills/<skill-name>/` path, preserve the complete directory, validate the
installation, and report the installed path. Restart only if Codex does not
detect the new skill automatically.

## License

MIT. See [LICENSE](LICENSE).
