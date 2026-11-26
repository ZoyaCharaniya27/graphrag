# FIX Checksum Calculation (tag 10)

In the FIX protocol, the CheckSum field (tag 10) is always the final field of a message. It is computed by summing the ASCII values of all bytes in the message up to but not including the checksum field, taking the result modulo 256, and formatting it as a three-digit value. The checksum lets the receiver detect transmission corruption.
