# Testing Strategy

This document explains how we will test the dotfiles pipeline.

Our goal is to make sure nothing breaks when we update programs or change configuration files.

Because this is a visual and system-level configuration, testing can be difficult.

We will split our testing into two parts: **Automated Testing** and **Manual Testing**.

## Automated Testing

We will use the **NixOS VM test framework** (`nixosTest`).

This is a free feature built into NixOS. It runs a virtual machine (VM) in the background during our GitHub Actions pipeline.

The VM allows us to boot our system, start a graphical environment (like `i3`), and simulate typing or clicking. We can also take screenshots to verify if things look right.

Because VM tests can take **10 to 20 minutes**, we will only run them on Pull Requests (PRs), not on the `master` branch. This saves GitHub Actions minutes and money.

Below is the automated testing strategy for each **Role**.

### Role: i3 (Window Manager)

**What we will test automatically:**
- Does the i3 window manager start without crashing?
- Can we open the `rofi` menu by simulating the `Super+d` (Mod+d) keybind?
- Can we open a terminal using the `Super+Enter` keybind?
- Does the `polybar` status bar start automatically?

**How we test it:**
- We write a Nix test script that waits for `i3` to start.
- We send the keystrokes to the VM using `machine.send_key()`.
- We wait to see the window appear, or we take a screenshot and check for specific text using OCR (Optical Character Recognition).

### Role: Neovim

**What we will test automatically:**
- Does `nvim` open without throwing syntax errors in the Lua configuration?
- Are the language servers (like PHP actor, PHPStan) installed and recognized by Neovim?

**How we test it:**
- Run `nvim --headless -c 'qa'` in the terminal. If it exits cleanly, the basic config is correct.
- We can also create a dummy `.php` file in the test VM. Then, we open Neovim and run a command to check if the LSP attaches successfully.

### Role: PHP

**What we will test automatically:**
- Is the correct PHP version installed?
- Are global tools installed properly? (like `composer`, `phpstan`, `phpmd`)
- Can we create a new PHP project from the template and run it?

**How we test it:**
- The VM test can run `php -v` and `composer --version`.
- We can execute `phpstan --version` to make sure it exists.

### Role: CLI & Shell (Zsh, Bash)

**What we will test automatically:**
- Does the shell load the configuration and aliases correctly?
- Are standard tools installed? (like `git`, `wget`, `jq`, `fzf`)

**How we test it:**
- Start a `zsh` process in the VM.
- Run a simple command or check an alias to make sure the `.zshrc` loaded without errors.

### Role: Docker

**What we will test automatically:**
- Does the Docker daemon start correctly?
- Can a standard user run a basic Docker command without using `sudo`?

**How we test it:**
- We wait for the `docker.service` to start.
- We run `docker run hello-world` as the `joey` user.

### Role: GUI Apps & Fonts

**What we will test automatically:**
- Are fonts loaded properly by the system?
- Do GUI apps like Chrome or LibreOffice launch without missing libraries?

**How we test it:**
- We run a command like `fc-list | grep ComicShanns` to verify the font is present.
- We can try launching Chrome in the background to ensure it doesn't immediately crash.

---

For things that cannot be tested automatically, please read the `MANUAL_TESTING.md` document.
