# FIX Protocol Versions

The FIX protocol has evolved through several versions. FIX 4.2 and FIX 4.4 remain widely deployed for order routing. FIX 5.0 introduced the FIXT transport layer, which separates the session layer from the application layer so that the application version can evolve independently. The BeginString (tag 8) identifies the session protocol version, such as FIX.4.4 or FIXT.1.1.
