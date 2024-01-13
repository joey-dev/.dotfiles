Vagrant.configure("2") do |config|
  config.ssh.private_key_path = "~/.ssh/id_rsa"
  config.ssh.forward_agent = true

  config.vm.box = "gusztavvargadr/ubuntu-desktop"

  config.vm.synced_folder "~/.dotfilesb", "/home/vagrant/.dotfiles"
  config.vm.synced_folder ".", "/vagrant"

  config.vm.provider "virtualbox" do |vb|
    vb.gui = true
    vb.memory = "1024"
  end
end
