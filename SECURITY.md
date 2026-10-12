# Security policy

There are two kinds of security problem you might find. They go to different
places:

| You found a problem in… | Report it to | Section |
| --- | --- | --- |
| **This project**: the bridge code, its CI, the container image or the dashboard | This repository, privately | [Reporting a vulnerability in this project](#reporting-a-vulnerability-in-this-project) |
| **Mazda's or Changan's systems**: the cloud API, the Mazda app, or the car | Mazda, or a vulnerability coordinator. **Not** this repository. | [Vulnerabilities in Mazda's systems](#vulnerabilities-in-mazdas-systems) |

This is an independent, unofficial hobby project. It isn't made, endorsed or
supported by Mazda Motor Corporation or Changan Automobile, and it can't fix,
and doesn't speak for, anything on their side.

## Reporting a vulnerability in this project

**Don't open a public issue.** Report it privately through GitHub:
**Security → Report a vulnerability** on this repository
([direct link](https://github.com/Yornik/mazda6e-grafana-bridge/security/advisories/new)).

Please include:

- what's affected (file, version or image tag);
- how to reproduce it, ideally against the test setup in `tests/` rather than
  a real account;
- what an attacker could do with it.

**Never include real credentials, device IDs, VINs, tokens or locations**, not
even your own. Redact them as `<redacted>`.

This is maintained in spare time, so handling is best effort:

- **Acknowledgement:** within 7 days.
- **Fix:** shipped as a new release, as soon as one is ready.
- **Disclosure:** coordinated with you, and a GitHub security advisory credits
  you unless you'd rather not be named.

### What's in scope

The things that matter most, given that the bridge holds credentials that can
drive a car:

- **Bypassing read-only.** Any way to make the bridge send a request outside
  `READ_ONLY_PATHS`, or to get past the CI read-only guard
  (`scripts/check_read_only.py`). This is the most important class.
- **Credential exposure.** `MAZDA_EMAIL`, `MAZDA_PASSWORD`, `MAZDA_DEVICE_ID`
  or a session token ending up in logs, metrics, error messages, the image or
  CI output.
- **Metrics leaking more than documented**, for example a location exported
  while `EXPORT_LOCATION` is off.
- **The `/metrics` endpoint** being usable for anything beyond reading metrics.
- **Supply chain:** the image, the GitHub Actions workflows, dependency
  pinning, or the release process.

### Supported versions

Only the latest release gets security fixes. Run the newest
`ghcr.io/yornik/mazda6e-grafana-bridge` tag.

### Known and accepted, not vulnerabilities

- **The credentials are powerful by design.** Email, password and a verified
  device ID together are a full login to the Mazda account. This is how
  Mazda's login works, and the README's warning covers it.
- **`/metrics` has no authentication**, like every Prometheus exporter. It
  shows vehicle state, and location if enabled. Keep it on a trusted network,
  or restrict who can reach it (for example with a NetworkPolicy).
- **The client imitates the official iOS app's headers.** The backend requires
  that. It's documented, not hidden.

## Vulnerabilities in Mazda's systems

If you find a weakness in the **Mazda cloud API, the Mazda app, the Changan
backend (`*.changanauto.*`) or the vehicle itself**, this project can't fix it.
Please:

1. **Don't publish it**: not in an issue, pull request, discussion or commit
   here. A public write-up could let people unlock or track cars that aren't
   theirs.
2. **Report it to Mazda through a coordinator.** We couldn't find a published
   security contact or vulnerability disclosure program for Mazda or Changan:
   no `security.txt` on mazda.com, mazda.eu or mazda.de. These coordinators
   exist precisely to get such reports to the right team and handle
   disclosure:
   - **[JPCERT/CC](https://www.jpcert.or.jp/english/vh/project.html)**:
     Japan's coordination centre. Mazda Motor Corporation is a Japanese
     company.
   - **Your national CSIRT in the EU.** Under the NIS2 Directive (article 12)
     every member state designates a CSIRT to coordinate vulnerability
     disclosure. The [CSIRTs Network](https://csirtsnetwork.eu/) lists them;
     for example, the Netherlands' is the
     [NCSC](https://www.ncsc.nl/producten-en-diensten/kwetsbaarheid-melden-cvd).
   - **[CERT/CC](https://kb.cert.org/vuls/report/)**: the US coordinator,
     which also handles reports for vendors outside the US.

   If Mazda publishes its own disclosure channel later, use that instead, and
   please open an issue here so this file can be updated.
3. **Only test what you own.** Use your own account and your own car. Don't
   access other people's accounts or vehicles, don't send commands to a car,
   and stop as soon as you can show the problem exists. This bridge is
   read-only on purpose and isn't a testing tool.
4. **If you think your own account or car has been compromised**, change your
   Mazda password and control PIN in the app, then contact Mazda customer
   service or your dealer.

Reporting a Mazda or Changan issue here is welcome only as a heads-up that
something in this project should change. For example: "the condition endpoint
now returns other users' data, the bridge should stop calling it". Send that
privately as well.

## Disclaimer

This project and its maintainers aren't affiliated with Mazda Motor
Corporation or Changan Automobile. **Mazda** and **Mazda 6e** are trademarks of
Mazda Motor Corporation. The software is provided "as is", without warranty;
see [LICENSE](LICENSE), sections 7 and 8.
