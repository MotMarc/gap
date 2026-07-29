# Compatibility policy

GAP uses semantic versioning for the application and SDK. Patch releases
preserve public imports, method signatures, CLI commands/exit codes, HTTP
routes/schemas and v1 formats. Minor releases may add optional fields and
capabilities. Removal requires documentation, at least one minor release of
deprecation, and a major version.

Historical v0.15/v0.16 objects remain accepted by their declared profiles.
Extension fields are signed and must not alter defined semantics. Unknown
profiles and unsupported major versions fail closed; discovery is capability
metadata, never a trust root. Security defects may require a breaking change
with an advisory, migration path, compatibility rationale and explicit version
boundary.
