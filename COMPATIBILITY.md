# Compatibility

| Platform / equipment | Discovery and radar | Block / unblock |
| --- | --- | --- |
| Windows 10/11, private IPv4 network up to /24 | Implemented; permissions, isolation and ICMP affect results | Router dependent |
| Huawei EchoLife HG8546M, captured COMMON login flow | Yes on Windows | Experimental blacklist adapter; tested by the creator on one router setup |
| Other router brands and firmware | Discovery does not need router login | Not implemented |
| macOS / Linux | Demo UI only; live discovery not implemented | Unsupported in this release |
| iOS / Android | No native local discovery app | Unsupported |

This is a local program, not a cloud-hosted scanner. Each user runs it on their own Windows computer and supplies their own router credentials only if using a supported adapter. No admin password is bundled or shared. A router model name alone does not guarantee firmware compatibility.

Allowlist mode is manual. This app never enables existing blacklist rules automatically. Read-back verifies saved router configuration, not independently proven internet denial. A phone may have mobile data, random MACs or another connection. Verify blocking on a spare device and verify unblocking restores access.

For contributing a new router integration: document its legitimate admin interface, implement authentication, read all existing rules, preserve unrelated settings, protect the operator's MAC, avoid repeated writes, add synthetic fixture tests, and test with an authorized owner. Never commit captured credentials, cookies or session tokens.
