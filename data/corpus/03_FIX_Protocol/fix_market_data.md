# FIX Market Data Messages

In the FIX protocol, a MarketDataRequest is MsgType V and subscribes to quotes or trades. The venue responds with a MarketDataSnapshotFullRefresh (MsgType W) containing the full book snapshot or a MarketDataIncrementalRefresh (MsgType X) containing updates. MDEntryType (tag 269) distinguishes entry kinds, for example 0 for Bid, 1 for Offer, and 2 for Trade.
