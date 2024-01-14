#!/usr/bin/env bash

if [[ $1 != "unitAll" ]]
then
	LOCATION=$(rofi -dmenu -p "$1 test reference")
fi

TEST_PATH=$(echo "$LOCATION" | sed 's.\\./.g' | sed 's/Dyflexis//' | sed 's@//@@')
PATH_NAME=$TEST_PATH
PARAM="$1"

if [[ "$1" == "unit" ]]
then
	PARAM+=" --filter"
elif [[ "$1" == "unitAll" ]]
then
	PATH_NAME="unitAll"
	PARAM="unit"
	TEST_PATH=""
elif [[ "$1" == "acceptance" ]]
then
	PARAM+=" --group"
else
	TEST_PATH+=".php"
fi

if [[ $1 ]]; then
	/home/joey/Scripts/Windows/Services/addToRecent "$PATH_NAME" "xterm -hold -e 'cd ~/Code/Work/dyflexis-monorepo/ && ./test_runner.sh debug $PARAM $TEST_PATH'"

	xterm -hold -e "cd ~/Code/Work/dyflexis-monorepo/ && ./test_runner.sh debug $PARAM $TEST_PATH"
fi


