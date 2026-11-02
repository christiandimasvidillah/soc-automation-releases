# Troubleshooting

Start All partial failures: inspect SocMaster output, PID path, active slot, imports, service state, and timeout. Feature configured ON but effective OFF: fix dependencies. Privacy blocked: inspect residual categories and run regression/retest; never bypass. Missing Gemini credential: fix secret configuration and restart as required. Empty Service Health: verify endpoint type, cache, version, and refresh. Expired/hash/UUID-mismatched candidates must be rebuilt.

<!-- custom-root-launcher-v1.27.9 -->
## Launcher looks for `.venv` under the wrong root

Use launcher v1.27.9 or newer. Verify `.installation-root`, then run `manager/soc-tui --root <root>` when an explicit override is required.

<!-- cumulative-installer-generation-v1.27.10 -->
## Generated install.py syntax error

The nested-newline defect in v1.27.9 is resolved by v1.27.10. Builds now fail closed on compile, extraction, checksum, custom-root simulation, and launcher gates.

<!-- cumulative-installer-generation-v1.27.11 -->
## Generated install.py syntax error

The nested-newline defect in v1.27.9 is resolved by v1.27.10. Builds now fail closed on compile, extraction, checksum, custom-root simulation, and launcher gates.
