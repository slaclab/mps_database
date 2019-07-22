#!/usr/bin/env bash

# Database names
NAMES="mps thr_base thr analog_input"

# File names
for n in $NAMES
do
    SUBSTITUTION_FILE=$n.substitutions
    TEMPLATE_FILE=$n.template

    echo "=== Processing $SUBSTITUTION_FILE file ==="

    echo "  Removing previous files: \"$TEMPLATE_FILE\"..."
    rm -f $TEMPLATE_FILE

    echo "  Generating template file \"$TEMPLATE_FILE\" from substitution file \"$SUBSTITUTION_FILE\""
    msi -S $SUBSTITUTION_FILE -o $TEMPLATE_FILE
    if [ "$?" != "0" ]; then
      echo "ERROR: Failed to generate template file!"
    else
      echo "  The database template was generated as \"$TEMPLATE_FILE\""
    fi

    echo ""
done
