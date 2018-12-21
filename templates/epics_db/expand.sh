#!/usr/bin/env bash

# Database names
NAMES="mps thr_base thr"

# File names
for n in $NAMES
do
    SUBSTITUTION_FILE=$n.substitutions
    TEMPLATE_FILE=$n.template

    echo "Removing previous files: \"$TEMPLATE_FILE\"..."
    rm -f $TEMPLATE_FILE
    echo "Done!"
    echo ""

    echo "Genereting templete file \"$TEMPLATE_FILE\" from substitution file \"$SUBSTITUTION_FILE\""
    msi -S $SUBSTITUTION_FILE -o $TEMPLATE_FILE
    echo "Done!"
    echo ""

    echo "The database template was generated as \"$TEMPLATE_FILE\""
    echo ""
done