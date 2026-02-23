{
  description = "NixOS dotfiles configuration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, home-manager, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      
      # Function to create home configuration for a user
      # Optionally pass a list of extra modules (e.g., a private git config file)
      mkHomeConfiguration = { username, extraModules ? [] }:
        home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          
          modules = [
            ./home.nix
            {
              home.username = username;
              home.homeDirectory = "/home/${username}";
            }
          ] ++ extraModules;
        };
    in
    {
      homeConfigurations = {
        # Default configuration for CI and testing
        user = mkHomeConfiguration { username = "user"; };
        
        # You can add your personal configuration by uncommenting and editing:
        # To include a private git config (with your name/email), create
        # ~/.git_private.nix and add it as an extra module:
        # yourname = mkHomeConfiguration {
        #   username = "yourname";
        #   extraModules = [ /home/yourname/.git_private.nix ];
        # };
      };

      # Checks that run when you do `nix flake check`
      checks.${system} = {
        # This checks that the home-manager configuration can be built
        home-manager = self.homeConfigurations.user.activationPackage;
      };
    };
}
