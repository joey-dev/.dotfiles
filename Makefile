install:
	sudo apt -y install ansible
	# do git stuff

sshtoken:
	echo 'hi'

provision:
	ansible-playbook -i ./hosts playbook.yml -e ansible_python_interpreter=/usr/bin/python3
	echo "please logout, select i3 at the bottom right, then login"

install-test:
	#sudo apt -y install virtualbox
	#sudo apt -y install virtualbox-dkms
	#sudo apt -y install linux-headers-generic
	curl -O https://releases.hashicorp.com/vagrant/2.4.0/vagrant_2.4.0-1_i686.deb
	sudo apt -y install ./vagrant_2.4.0-1_i686.deb

test:
	vagrant up

