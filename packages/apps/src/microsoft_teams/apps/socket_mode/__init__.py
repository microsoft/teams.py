"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Socket Mode transport: an outbound WebSocket that receives activities without the
# bot needing a public inbound HTTPS endpoint.
#
# The layers, innermost first:
#
# * :mod:`signalr` -- SignalR JSON hub wire format. No Teams concepts, no SDK imports.
# * :mod:`envelope` -- Teams activity envelopes and reply frames. Pure functions.
# * :mod:`negotiate` -- the HTTP negotiate handshake and all transport-security checks.
# * :mod:`connection` -- one WebSocket: handshake, ``SocketReady`` gate, dispatch, teardown.
# * :mod:`geo_socket` -- supervises one geography: retry, reconnect, generation fencing, refresh.
# * :mod:`transport` -- fans out across geographies and owns start/stop.
#
# This package is internal and intentionally exports nothing; the public Socket Mode
# surface is added separately.
