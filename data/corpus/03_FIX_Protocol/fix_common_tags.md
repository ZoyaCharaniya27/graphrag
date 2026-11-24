# Common FIX Tags

Common FIX tags include tag 8 BeginString which identifies the FIX version, tag 9 BodyLength, tag 35 MsgType, tag 49 SenderCompID, tag 56 TargetCompID, tag 34 MsgSeqNum, and tag 10 CheckSum. The BeginString always appears first and the CheckSum always appears last. The MsgSeqNum is used to detect gaps and ensure ordered delivery within a FIX session.
