#!/bin/bash
: '
##Decription:
$1: input file
$2: output file
$3: time delta between frames
$4: total frames
########
'
for i in `seq 0 $4`
do
        if [ 1 -eq "$(echo "${i}*${3} < 1" | bc)" ]
        then
                position=0
        else
                position=$(echo "$3*$i" | bc)
        fi
        ffmpeg -v error -y -accurate_seek -ss $position -i $1 -filter:v scale="-1:50" -frames:v 1 $2$i.png
done