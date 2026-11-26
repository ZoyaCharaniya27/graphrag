# FIX Order Types (OrdType tag 40)

In the FIX protocol, the OrdType field (tag 40) specifies the order type. Common values are 1 for Market, 2 for Limit, 3 for Stop, and 4 for Stop Limit. A Limit order requires a Price (tag 44). A Stop order requires a StopPx (tag 99). The TimeInForce field (tag 59) qualifies how long the order remains active, for example 0 for Day and 1 for Good Till Cancel.
