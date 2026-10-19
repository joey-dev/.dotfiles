{
  pkgs,
  lib,
  username,
  roles,
  home-manager,
}:

pkgs.testers.runNixOSTest {
  name = "dotfiles-e2e-test";

  nodes.machine =
    { config, pkgs, ... }:
    {
      imports = [
        ../roles/system.nix
        ../hosts/common.nix
        home-manager.nixosModules.home-manager
      ];

      # Enable all roles for the test
      roles = lib.genAttrs roles (_: { enable = true; });

      # Configure Home Manager for the test user
      home-manager.useGlobalPkgs = true;
      home-manager.useUserPackages = true;
      home-manager.users.${username} = {
        imports = [ ../roles ];
        roles = lib.genAttrs roles (_: { enable = true; });
        home.stateVersion = "24.05";
        # Workaround to allow home-manager to set up the home directory in the VM
        home.homeDirectory = lib.mkForce "/home/${username}";
      };

      # Set a dummy password for the test user to allow sudo, and enable auto-login
      users.users.${username}.password = "test";
      services.xserver.displayManager.autoLogin.enable = true;
      services.xserver.displayManager.autoLogin.user = username;

      # Speed up the test by avoiding heavy unneeded services if possible
      # But we need i3, X11, etc. which are pulled in by roles
      virtualisation.memorySize = 2048;
      virtualisation.diskSize = 4096;
    };

  testScript = ''
    start_all()

    # Wait for the machine to boot and X11 to start (auto-login into i3)
    machine.wait_for_unit("display-manager.service")
    machine.wait_for_x()

    # 1. Test Window Manager (i3) and Terminal (Alacritty)
    # Give i3 a moment to fully initialize
    machine.sleep(2)
    # Open terminal using Super+Enter (Mod4+Return)
    machine.send_key("meta-ret")
    machine.wait_for_window("Alacritty")

    # 2. Test App Launcher (Rofi)
    # Open rofi using Super+d
    machine.send_key("meta-d")
    machine.sleep(1)
    machine.screenshot("rofi_open")

    # 3. Test Shell (Zsh)
    # Run a command inside zsh as the user to ensure it loads without crashing
    machine.succeed("su - ${username} -c 'zsh -c \"echo shell works\" | grep works'")

    # 4. Test Neovim
    # Verify Neovim opens headlessly without Lua errors
    machine.succeed("su - ${username} -c 'nvim --headless -c qa'")

    # 5. Test PHP and Tools
    machine.succeed("su - ${username} -c 'php -v'")
    machine.succeed("su - ${username} -c 'composer --version'")
  '';
}
