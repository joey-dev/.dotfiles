# NixOS side of the ai role: a separate rootless Docker daemon for claude-workflow.
# The workflow's compose stack runs as the user `cw-docker`, so code Claude wrote
# can't reach /home/<username> through a bind mount. See docs/12 (option 2) and docs/13.
{
  config,
  lib,
  username,
  ...
}:

let
  # Container uid/gid 1000 maps to host subuid-start + 1000 - 1.
  containerUser = "200999";
in
{
  options.roles.ai.dockerSandbox.enable = lib.mkEnableOption "the rootless Docker daemon (user cw-docker) for claude-workflow";

  config = lib.mkIf (config.roles.ai.enable && config.roles.ai.dockerSandbox.enable) {
    virtualisation.docker.rootless = {
      enable = true;
      # Never true: it would point DOCKER_HOST of every user (and the dev stack) at rootless.
      setSocketVariable = false;
      # Outside /run: rootlesskit copies up /run, so a socket there is invisible to the host.
      daemon.settings = {
        hosts = [ "unix:///var/lib/cw-docker-sock/docker.sock" ];
        # Socket group. The default "docker" resolves to the host's root-docker gid (131),
        # which maps to subgid 200130 inside the user namespace. Gid 0 inside maps to
        # cw-docker's own gid (2001), so the user reaches the socket via that group.
        group = "0";
      };
    };

    # The module defines the user service for every non-root user; only cw-docker runs it.
    systemd.user.services.docker.unitConfig.ConditionUser = lib.mkForce "cw-docker";

    users.groups.cw-docker.gid = 2001;

    users.users.cw-docker = {
      # dockerd-rootless.sh needs $HOME, so a normal user with a home.
      isNormalUser = true;
      uid = 2001;
      group = "cw-docker";
      # Start its user manager (and the daemon) at boot, without a login.
      linger = true;
      # Must never contain uid 1000 (the user's own uid).
      autoSubUidGidRange = false;
      subUidRanges = [
        {
          startUid = 200000;
          count = 65536;
        }
      ];
      subGidRanges = [
        {
          startGid = 200000;
          count = 65536;
        }
      ];
    };

    # The user talks to the rootless socket through this group.
    users.users.${username}.extraGroups = [ "cw-docker" ];

    # The rootless stack publishes 80/443 like the dev stack.
    boot.kernel.sysctl."net.ipv4.ip_unprivileged_port_start" = 80;

    # Shared worktree folder: the user, cw-docker (container root) and container uid 1000
    # can all read, write and delete. Default ACLs make new files inherit these rights.
    systemd.tmpfiles.rules = [
      "d /var/lib/cw-docker-sock 0750 cw-docker cw-docker -"
      "d /srv/claude-workflow 0750 ${username} cw-docker -"
      "A+ /srv/claude-workflow - - - - u:${containerUser}:x,g:${containerUser}:x"
      "d /srv/claude-workflow/worktrees 2770 ${username} cw-docker -"
      # "Other" gets read (+ X = execute only on dirs and executables): images COPY worktree
      # files with their mode, and services that drop to their own uid (lighttpd, www-data)
      # must read them. Host users still can't reach it: /srv/claude-workflow is 0750.
      "A+ /srv/claude-workflow/worktrees - - - - u:${username}:rwx,g:cw-docker:rwx,u:${containerUser}:rwx,g:${containerUser}:rwx,o::rX,m::rwx,d:u:${username}:rwx,d:g:cw-docker:rwx,d:u:${containerUser}:rwx,d:g:${containerUser}:rwx,d:o::rX,d:m::rwx"
    ];
  };
}
