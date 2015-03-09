#!/bin/sh

{{ executable }} \
{% for key, value in flags.iteritems() %}       -{{key}} {{value}} \
{%endfor%} > output.txt
