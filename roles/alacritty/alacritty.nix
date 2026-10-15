{ config, lib, ... }:

{
  options.roles.alacritty.enable = lib.mkEnableOption "the alacritty role";

  config = lib.mkIf config.roles.alacritty.enable {
    programs.alacritty.enable = true;

    # Link Alacritty configuration
    xdg.configFile."alacritty/alacritty.toml".source = ./configuration/alacritty.toml;
  };
}
