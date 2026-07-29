# Media Binding

GAP 0.16 supports native embedding only for PNG through
`gap-png-embedded-v1`. A bounded structural parser validates the signature,
chunk lengths, chunk types, CRCs, IHDR/IEND ordering, duplicate GAP chunks,
truncation, trailing bytes, and metadata size. It never decodes image pixels.

The digest is calculated over the exact PNG with only the designated `gaPc`
credential chunk removed. This resolves the circular digest while protecting
image data, ordinary metadata, chunk order, and every unrelated byte.
Replacement is refused by default. Future formats require separate profiles;
this release does not claim C2PA, JPEG, PDF, or video support.
