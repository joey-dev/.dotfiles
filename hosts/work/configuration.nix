# The work laptop. Shared settings are in ../common.nix.
_:

{
  imports = [ ./hardware-configuration.nix ];

  # Encrypted swap partition
  boot.initrd.luks.devices."luks-82880ca9-358e-4989-88ca-5545f36d43de".device =
    "/dev/disk/by-uuid/82880ca9-358e-4989-88ca-5545f36d43de";

  # This value determines the NixOS release from which the default
  # settings for stateful data, like file locations and database versions
  # on your system were taken. It's perfectly fine and recommended to leave
  # this value at the release version of the first install of this system.
  system.stateVersion = "25.11";
}
