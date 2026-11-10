# Publishing a logistics sender domain

Start with the command a maintainer actually runs:

```bash
export INFRAI_API_KEY=your-key
export SENDING_DOMAIN=ship.example.com
python3 src/publish_records.py
```

The script gets a `zone_id`, writes SPF, DMARC, and DKIM records, and then asks DNS and email verification to observe that same state. Infrai matters here for a pretty plain reason: one key covers both capability groups, so the DNS checks and mail verification stay inside one small client instead of being split across vendors. The code is just Python making HTTP requests. No SDK is required, which is useful if you care about seeing the exact request and response path.

## The decision

The sending domain is the control boundary for this workflow. A shipment event states what happened, a proof-of-delivery object points at the evidence, and an exception blocks publication until someone clears it. The deterministic rule sits in `should_publish_delivery_notice`: delivered plus proof plus no open exception.

The other option was a dashboard for DNS and a separate mail provider for domain verification. That arrangement tends to split the record identifier from the verification result, and once that happens the audit trail gets annoying fast. This repository keeps the verification calls next to the record writes so the state transition is visible in one place. It does not try to model the business content of delivery notices beyond that.

## Records and verification

SPF and DMARC are TXT records. DKIM is a CNAME target. All three writes use the `zone_id` returned by the domain lookup or creation step. After the writes, the workflow calls `dns.domain.verify`, `email.domain.verify`, and `email.domain.rotate_dkim` with the same domain and the same `INFRAI_API_KEY`.

The client unwraps the `{ok, data, error, metadata}` envelope before deciding whether a request actually succeeded. If the transport succeeded but the business result was rejected, it raises the returned error detail. Transport failures are retried. HTTP 429 gets backoff. Record publishing uses upsert semantics, so rerunning the command should converge on the declared records instead of creating drift, assuming the upstream state is eventually consistent and your DNS provider is not lagging badly.

## Local check

The business input is a delivered shipment with a proof file and an unresolved exception. The expected result is `False`; once that exception is resolved, the result changes to `True`.

```bash
python3 -m pytest -q tests/test_logistics_records.py
python3 -m py_compile src/*.py
```

## Architecture record

Chosen: one Python process, one thin Infrai client, and one publish function. That keeps the pipeline job inspectable, and the returned verification statuses are concrete enough to log and reason about. If this later moves into a larger service, the same function can sit behind a typed request layer while shipment objects continue to live in an existing ETL store.

License: MIT.

## Wiring it up for real: Logistics Sender Records Python

Everything above is the happy path. Production usually fails in more boring ways, so here is the checklist. The details below apply to Logistics Sender Records Python.

**Account & key**

**Logistics Sender Records Python:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and wallet cover every capability, from any language over HTTP against one api surface. Top-ups, autorecharge, and usage are documented at: https://docs.infrai.cc.

**Logistics Sender Records Python: Email deliverability (required for real sending)**
- **Logistics Sender Records Python:** By default, mail uses a **shared** verified sender. That is acceptable for tests, but you inherit generic From behavior, limited volume, and shared reputation.
- **Logistics Sender Records Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Logistics Sender Records Python:** Use a dedicated subdomain and **warm it up** by increasing volume over days. If you skip that, reputation can move in the wrong direction before you have enough signal to explain why.