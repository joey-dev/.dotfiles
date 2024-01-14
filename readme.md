# starting
run:
- make install
- make provision

do the following shortcuts:
- win + shift + r (anywhere)
- alt + r (in the terminal)

# testing first time
run: 
- make install-test
- ssh-keygen -f "/home/{username}/.ssh/known_hosts" -R "[127.0.0.1]:2222"
- make test
- ssh-copy-id -p 2222 vagrant@127.0.0.1
- make test-reload

# testing again, clean
run:
- make test-new
- ssh-copy-id -p 2222 vagrant@127.0.0.1
- make test-reload

# testing
run:
- make test
