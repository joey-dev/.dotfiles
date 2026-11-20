new branches, ordered by depended on. number 1 is depended on master:
1. Live-link the nvim, i3, and polybar config
  - commit hash: 1caf64c3
  - is already a different branch, so this one is fine
2. rename flake template
  - commit hash: 729508b
  - extract the flake.nix change + templates/php-symfony > templates/latest move
3. Add windows into nixos using wsl
  - commit hash: 51e1791b
4. fix nix and lightshot
  - commit hash: 4b1d26a0
  - this commited an error, so also add this commit hash into it: 9331d2cf
5. testing
  - only has changes for ai
  - keep the branch name this for now



