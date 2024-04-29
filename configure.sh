#!/bin/bash

# Function to check if an option is already configured in configured.env
is_option_configured() {
    option=$1
    if grep -q "^$option=" configured.env; then
        return 0  # Option is configured
    else
        return 1  # Option is not configured
    fi
}

# Function to add an option to configured.env
add_option_to_config() {
    option=$1
    echo "$option=yes" >> configured.env
}

# Function to prompt user and configure options
configure_option() {
    option=$1
    read -p "Did you configure $option? (yes/no): " answer
    if [ "$answer" = "yes" ]; then
        add_option_to_config $option
    fi
}

# Main script
touch configured.env  # Create configured.env if it doesn't exist

# Loop through each option and configure if not already configured
options=("generate_ssh_key" "link_ssh_key_to_github" "link_ssh_key_to_home_server" "setup_protonpass" "import_dbeaver_settings" "setup_wireguard" "configure_meld")
for option in "${options[@]}"; do
    if ! is_option_configured "$option"; then
        configure_option "$option"
    fi
done

