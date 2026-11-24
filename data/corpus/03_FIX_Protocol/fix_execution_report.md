# FIX ExecutionReport (MsgType 8)

In the FIX protocol, an ExecutionReport message is identified by MsgType (tag 35) with a value of 8. It communicates the status of an order. ExecType (tag 150) describes the reason for the report, and OrdStatus (tag 39) describes the current order state, for example 0 for New, 1 for Partially filled, 2 for Filled, and 4 for Canceled. LastQty (tag 32) and LastPx (tag 31) report the quantity and price of the most recent fill.
