# FIX Reject and Business Reject

In the FIX protocol, a session-level Reject (MsgType 3) indicates a message could not be processed due to a session-level rule violation, such as an invalid tag. A BusinessMessageReject (MsgType j) indicates an application-level rejection, carrying RefMsgType (tag 372) and a BusinessRejectReason (tag 380) that explains why the message was rejected.
