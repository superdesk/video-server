#!/bin/bash
: '
##Decription:
$1: input file
$2: output file
$3: delta time every picture,
$4: total frames
########
'
for i in `seq 0 $4`
do
        if [ 1 -eq "$(echo "${i}*${3} < 1" | bc)" ]
        then
                num= bc -l <<<"$3*$i"
                ffmpeg -y -accurate_seek -ss `echo 0$num | bc` -i $1 -filter:v scale="-1:50" -frames:v 1 $2$i.bmp
        else
                ffmpeg -y -accurate_seek -ss `echo $i*$3 | bc` -i $1 -filter:v scale="-1:50" -frames:v 1 $2$i.bmp
        fi
done