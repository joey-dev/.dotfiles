# Home Manager settings for the work laptop only.
_:

{
  # Monitor layouts, picked with Win+m or `autorandr --change`.
  # To add one: arrange the screens (arandr), run `autorandr --save <name>`,
  # then copy ~/.config/autorandr/<name>/{setup,config} into a profile here.
  programs.autorandr.profiles = {
    # Laptop screen only
    primary = {
      # `setup` file: output name -> EDID of the screen connected to it
      fingerprint = {
        eDP-1 = "00ffffffffffff0006afa6340000000027200104a5221378033285a854499b250e505400000001010101010101010101010101010101203780b4703828406c30aa0058c110000018203780b4703858426c30aa0058c11000001800000000000000000000000000000000000000000002000c2dff103cc840081ac8202020010970207902002200143f2702847f07b3006b802f0037042700090009002501093f27023f2702283c80810010721a00000301283c0000605060503c00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000007890";
      };
      # `config` file: how each output is set up
      config = {
        eDP-1 = {
          primary = true;
          mode = "1920x1080";
          position = "0x0";
          rate = "60.00";
        };
        HDMI-1.enable = false;
        DP-1.enable = false;
        DP-2.enable = false;
        DP-3.enable = false;
        DP-4.enable = false;
      };
    };
  };
}
