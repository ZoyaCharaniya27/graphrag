# FIX NewOrderSingle (MsgType D)

In the FIX protocol, a NewOrderSingle message is identified by MsgType (tag 35) with a value of D. It is used to submit a single order to a broker or exchange. Key fields include ClOrdID (tag 11) the client order id, Symbol (tag 55), Side (tag 54) where 1 is Buy and 2 is Sell, OrderQty (tag 38), and OrdType (tag 40) where 1 is Market and 2 is Limit. A limit order also carries Price (tag 44).
