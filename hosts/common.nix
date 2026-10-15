# NixOS settings shared by every host.
# Role-specific system settings live in roles/<name>/system.nix.
{ username, ... }:

{
  # Bootloader
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  networking.networkmanager.enable = true;

  time.timeZone = "Europe/Amsterdam";

  i18n.defaultLocale = "en_US.UTF-8";
  i18n.extraLocaleSettings = {
    LC_ADDRESS = "nl_NL.UTF-8";
    LC_IDENTIFICATION = "nl_NL.UTF-8";
    LC_MEASUREMENT = "nl_NL.UTF-8";
    LC_MONETARY = "nl_NL.UTF-8";
    LC_NAME = "nl_NL.UTF-8";
    LC_NUMERIC = "nl_NL.UTF-8";
    LC_PAPER = "nl_NL.UTF-8";
    LC_TELEPHONE = "nl_NL.UTF-8";
    LC_TIME = "nl_NL.UTF-8";
  };

  # Keymap in X11
  services.xserver.xkb = {
    layout = "us";
    variant = "";
  };

  # Automount USB drives and other removable media
  services.devmon.enable = true;
  services.gvfs.enable = true;
  services.udisks2.enable = true;

  # Set a password with `passwd` after the first install
  users.users.${username} = {
    isNormalUser = true;
    description = "Joey";
    extraGroups = [
      "networkmanager"
      "wheel"
    ];
  };

  nixpkgs.config.allowUnfree = true;

  nix.settings = {
    experimental-features = [
      "nix-command"
      "flakes"
    ];
    # Replace identical files in the store with hard links
    auto-optimise-store = true;
  };

  # Remove old generations once a week
  nix.gc = {
    automatic = true;
    dates = "weekly";
    options = "--delete-older-than 14d";
  };

  # `nh os switch` / `nh home switch`, with a diff of what changed
  programs.nh = {
    enable = true;
    flake = "/home/${username}/.dotfiles";
  };
}
