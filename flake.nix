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
      mkHomeConfiguration = username: home-manager.lib.homeManagerConfiguration {
        inherit pkgs;
        
        modules = [
          ./home.nix
          {
            home.username = username;
            home.homeDirectory = "/home/${username}";
          }
        ];
      };
    in
    {
      homeConfigurations = {
        # Default configuration for CI and testing
        user = mkHomeConfiguration "user";
        
        # You can add your personal configuration by uncommenting and editing:
        # yourname = mkHomeConfiguration "yourname";
      };

      # Checks that run when you do `nix flake check`
      checks.${system} = {
        # This checks that the home-manager configuration can be built
        home-manager = self.homeConfigurations.user.activationPackage;
      };
    };
}
