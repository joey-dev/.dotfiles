# Check if playbook.yml exists
if [ ! -f "playbook.yml" ]; then
	echo "Error: playbook.yml not found"
	exit 1
fi

# Check if playbook.yml contains role names
roles=$(ls -d roles/*/)
for role in $roles; do
	role_name=$(basename $role)
	if ! grep -q "\b$role_name\b" playbook.yml; then
		echo "Error: Role '$role_name' not found in playbook.yml"
		exit 1
	fi
done

# Check if playbook.yml contains #
if grep -q "#" playbook.yml; then
	echo "Error: playbook.yml contains '#'"
	exit 1
fi
