# starting
run:
- make install
- make provision

# testing
run: 
- make install-test
- ssh-keygen -f "/home/{username}/.ssh/known_hosts" -R "[127.0.0.1]:2222"
- ssh-copy-id -p 2222 vagrant@127.0.0.1
- make test
