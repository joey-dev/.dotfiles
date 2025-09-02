install:
	#sudo apt -y install ansible
	python3 -m pip install --user ansible
	# do git stuff

update:
	python3 -m pip install --upgrade --user ansible
	./configure.sh

configure:
	./configure.sh

sshtoken:
	echo 'hi'

provision:
	ansible-playbook -i inventory playbook.yml -e ansible_python_interpreter=/usr/bin/python3 --ask-become-pass
	echo "please logout, select i3 at the bottom right, then login"

install-test:
	#sudo apt -y install virtualbox
	#sudo apt -y install virtualbox-dkms
	#sudo apt -y install linux-headers-generic
	curl -O https://releases.hashicorp.com/vagrant/2.4.0/vagrant_2.4.0-1_i686.deb
	sudo apt -y install ./vagrant_2.4.0-1_i686.deb

test:
	vagrant up

test-reload:
	vagrant reload

test-new:
	vagrant destroy
