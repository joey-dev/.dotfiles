# Plan: split the `testing` branch

Source note: `~/notes/fix-branch.md`. Nothing has been changed in git yet.

## Rules

- **Each branch tip must pass `nix flake check`.** Single commits in between may still fail, as they do now.
- **Don't combine commits.** Mixed commits are **split** by file or hunk. Each piece keeps its original message, author and date.
- **Branches form a chain:** `master ← 1 ← 2 ← 3 ← 4 ← 5`.
- Work happens in `~/.dotfiles-master` on new branches. **`testing` is not touched, and nothing is pushed.**

## Why some pieces move

- **Branch 2:** the template in `729508b` fails `deadnix` (unused `self`, `old`) and `statix` (useless parentheses). I checked this by running both on a copy of the file. `4b1d26a` fixes the lint errors but breaks the flake, and `9331d2c` fixes that. So all three go together.
- **Branch 3:** `hosts/windows/home.nix` is `{}`, and `nixfmt` wants `{ }`. The fix from `4b1d26a` goes with it.
- **Branch 3:** the `ai` role doesn't exist before branch 5, so Windows uses `"claude"` for now.

## Branches

### 1. `i3/live-symlinks` (`1caf64c`)

- **No changes.** Leave it alone, even if `nix flake check` fails on it (only report it).

### 2. `rename-flake-template-to-latest` (on top of 1)

| From | Part |
|---|---|
| `729508b` | `flake.nix` templates output (`php-symfony` → `latest`) |
| `729508b` | move `templates/php-symfony` → `templates/latest` |
| `729508b` | todo line: "able to find all templates here with 1 command" |
| `8013818` | `.gitignore`: `/templates/*/flake.lock` |
| `4b1d26a` | `templates/latest/flake.nix` cleanup |
| `9331d2c` | all of it |
| **new commit** | `readme.md:51` and `:54`: `php-symfony` → `latest` |

### 3. `add-windows-using-wsl-to-nixos-config` (on top of 2)

| From | Part |
|---|---|
| `51e1791` | everything **except** `lazy-lock.json`. `flake.lock` stays as it is |
| change | `hosts/windows/roles.nix`: `"ai"` → **`"claude"`** |
| `4b1d26a` | `hosts/windows/home.nix`: `{}` → `{ }` |

### 4. `fixes` (on top of 3)

| From | Part |
|---|---|
| `729508b` | `gh` in `roles/cli/cli.nix` |
| `729508b` | remove `code-cursor` from `gui-editors.nix`, plus its readme line |
| `729508b` | remove Copilot: `lazyvim.json` + `lazy-lock.json` |
| `729508b` | phpstan parser fix in `linting.lua` |
| `729508b` | tmux-sessionizer: `~/Code/Worktrees` |
| `729508b` | todo line: "currently we use mason + nix…" |
| `51e1791` | `lazy-lock.json` |
| `4b1d26a` | `boot.tmp.cleanOnBoot` in `hosts/work/configuration.nix` |
| `4b1d26a` | `gui-editors.nix` drops `pkgs` |
| `4b1d26a` | picom autostart fix in `i3.nix` |
| `7382a95` | Makefile `switch-update` and `flake.lock` |

**After this:** you review `fixes`. Then you decide whether to split it into more branches, squash it, or leave it like this.

### 5. `testing-new` (on top of 4)

| From | Part |
|---|---|
| `729508b` | `claude` → `ai` role rename (`roles/ai`, `hosts/roles.nix`, the readme line) |
| change | **`hosts/windows/roles.nix`: `"claude"` → `"ai"`** |
| `729508b` | the rest of the `todo.txt` changes |
| `f54a89a` | `todo.txt` |
| `8013818` … `c5ec3e9` | every commit, with the non-AI parts above removed |
| `9331d2c` | dropped here (all of it is in branch 2) |

**About `todo.txt`:** only lines that still exist on `testing` move to the matching branch. All other back-and-forth stays in `testing-new`.

## Checks

1. **`nix flake check`** on the tips of branches 2–5. Branch 1 is only reported.
2. **`git diff testing testing-new`** must show **only** the readme fix (`php-symfony` → `latest`).
3. **`git log`** per branch, so you can see which commit went where.

## Separate steps (each needs your OK)

- Reset `testing` to `testing-new`. **Careful:** `testing` is checked out in `~/.dotfiles`, which your live config uses.
- Force-push `testing`, and push the new branches.
- Decide what to do with `fixes` (split, squash or keep).
