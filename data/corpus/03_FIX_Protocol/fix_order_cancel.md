# FIX Order Cancel and Replace

In the FIX protocol, an OrderCancelRequest is MsgType F and is used to cancel a previously submitted order. An OrderCancelReplaceRequest, MsgType G, modifies an existing order, for example changing quantity or price. Both reference the original order via OrigClOrdID (tag 41) and carry a new ClOrdID (tag 11). An OrderCancelReject, MsgType 9, is returned if the request cannot be honored.
