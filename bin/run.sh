#!/bin/bash

DNSBL_HOME="$(dirname "$(dirname "$(realpath -e "$0")")")" && export DNSBL_HOME
LOG="${DNSBL_HOME}"/last.log

declare -a ACTIONS=()

_has_action() {
  for action in "${ACTIONS[@]}"; do
    if [[ "${1}" == "${action}" ]]; then
      return 0
    fi
  done

  return 1
}

_exec() {
  if /usr/bin/python3 "${DNSBL_HOME}"/lib/dnsbl.py >> "${LOG}"; then
    return 0
  else
    return 166
  fi
}

_main() {
  if (( $# == 0 )); then
    ACTIONS+=('refresh')
  else
    for arg in "$@"; do
      if [[ "${arg}" == 'refresh' ]]; then
        ACTIONS+=('refresh') && break
      fi
    done
  fi

  if _has_action refresh; then
    _exec
    exit $?
  fi
}

_main "$@"

exit 0
