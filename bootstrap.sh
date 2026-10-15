#!/usr/bin/env bash
#
# First-time setup of a laptop from this repository.
# Usage: ./bootstrap.sh <host>     (a folder in hosts/, e.g. work or personal)

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

cd "$(dirname "$0")"

# Flakes may not be enabled yet on a fresh install
flakes=(--extra-experimental-features "nix-command flakes")

host="${1:-}"
if [[ -z "$host" || ! -d "hosts/$host" ]]; then
    echo "Usage: $0 <host>"
    echo "Available hosts: $(find hosts -mindepth 1 -maxdepth 1 -type d -printf '%f ')"
    exit 1
fi

echo "🚀 Starting NixOS Dotfiles Bootstrap for '$host'..."

# 1. Git details, kept out of the repo in ~/.gitconfig.local
write_git_config=true
if [[ -f ~/.gitconfig.local ]]; then
    read -r -p "$HOME/.gitconfig.local already exists. Overwrite it? [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] || write_git_config=false
fi

if $write_git_config; then
    read -r -p "Enter your Git Name (e.g., John Doe): " git_name
    read -r -p "Enter your Git Email (e.g., john@example.com): " git_email

    echo "📝 Writing ~/.gitconfig.local..."
    cat > ~/.gitconfig.local <<EOF
[user]
    name = $git_name
    email = $git_email
EOF
    echo "✅ Git config created."
fi

# 2. NixOS configuration (only once hosts/<host>/configuration.nix exists)
# Flakes only see files known to git, so stage the host's (new) files first
git add "hosts/$host"
if [[ -f "hosts/$host/configuration.nix" ]]; then
    echo "🏗️ Building and switching to the NixOS configuration for '$host'..."
    sudo nixos-rebuild switch --flake ".#$host" --option experimental-features "nix-command flakes"
else
    echo "⚠️ hosts/$host/configuration.nix does not exist yet, skipping NixOS. See hosts/$host/README.md."
fi

# 3. Home Manager, using the version pinned in flake.lock
echo "🏗️ Building and switching to the Home Manager configuration for 'joey@$host'..."
# Home Manager runs its own `nix build`, so it needs the flake flags too
nix "${flakes[@]}" run .#home-manager -- switch --flake ".#joey@$host" "${flakes[@]}"

echo "🎉 Bootstrap complete! Reboot so LightDM starts with the new i3 configuration."
