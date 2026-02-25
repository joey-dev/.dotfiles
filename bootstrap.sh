#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "🚀 Starting NixOS Dotfiles Bootstrap..."

# 1. Prompt for Git details
read -p "Enter your Git Name (e.g., John Doe): " git_name
read -p "Enter your Git Email (e.g., john@example.com): " git_email

# 2. Create the local git config
echo "📝 Writing ~/.gitconfig.local..."
cat > ~/.gitconfig.local <<EOF
[user]
    name = $git_name
    email = $git_email
EOF

echo "✅ Git config created securely."

# 3. Run the initial Home Manager switch
echo "🏗️ Building and switching to Home Manager configuration for 'joey'..."

# We use 'nix run' to fetch the home-manager executable temporarily and run it
nix run github:nix-community/home-manager -- switch --flake .#joey

echo "🎉 Bootstrap complete! You may need to log out and log back in for your window manager to load."