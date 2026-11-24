# FIX Session Management

A FIX session is established with a Logon message (MsgType A) and terminated with a Logout message (MsgType 5). Heartbeat messages (MsgType 0) are exchanged at the interval set by HeartBtInt (tag 108) to keep the session alive. If a participant detects a sequence gap it sends a ResendRequest (MsgType 2). A TestRequest (MsgType 1) forces the counterparty to send a Heartbeat.
