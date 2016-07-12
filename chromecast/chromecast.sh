#!/bin/sh

kill `pgrep -f castnow`
castnow "$1" --quiet
