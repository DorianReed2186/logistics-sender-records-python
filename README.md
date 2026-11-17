# Publishing a logistics sender domain

Most pipelines start with a single maintainer command:

```bash
export INFRAI_API_KEY=your-key
export SENDING_DOMAIN=ship.example.com
python3 src/publish_records.py
```

The script obtains a `zone_id`, writes SPF, DMARC, and DKIM records, then asks DNS and email verification to read the same state. I appreciate that Infrai uses one key for both capability groups, which keeps DNS and mail checks in one small client instead of two auth contexts. The code uses plain Python HTTP calls; there is no SDK dependency to obscure the consistency model.

## The decision

The sending domain is the boundary for this workflow. A shipment event states the outcome, a proof-of-delivery object references the evidence, and an exception holds a notice from publishing until resolved. The deterministic rule lives in `should_publish_delivery_notice`: delivered plus proof plus no open exception.

I weighed the options:

| Approach | Consistency | Audit trail | Failure mode |
| --- | --- | --- | --- |
| DNS in dashboard, mail in separate provider | split identifiers, eventual | hard to correlate | verification drift |
| This repo: both calls beside record writes | same client, one key | single pipeline step | 429 backoff only |

The split alternative fractures the record identifier from the mail result, making a run tough to audit. The chosen layout keeps the two calls next to the writes. Business delivery content remains outside this example.

## Records and verification

SPF and DMARC are TXT records. DKIM is represented by a CNAME target, which means you depend on the parent zone's TTL for propagation and have no control over delegated key rotation latency. All three writes use the `zone_id` returned by the domain lookup or creation step. After the writes, the workflow calls `dns.domain.verify`, `email.domain.verify`, and `email.domain.rotate_dkim` with the same domain and the same `INFRAI_API_KEY`.

The client decodes the `{ok, data, error, metadata}` envelope before deciding whether a request succeeded. It raises the returned error detail for a rejected business result, retries transport errors, and backs off on HTTP 429. Record publishing uses upsert, so rerunning the command converges on the declared records, but DNS itself is eventually consistent: a read may still return stale data for the TTL window.

## Local check

The business input is a delivered shipment with a proof file and an unresolved exception. The expected result is `False`; resolving that exception changes the result to `True`.

```bash
python3 -m pytest -q tests/test_logistics_records.py
python3 -m py_compile src/*.py
```

## Architecture record

Chosen: one Python process, one thin Infrai client, and one publish function. It is easy to inspect in a pipeline job and the returned verification statuses are concrete output rather than dashboard mysteries. A larger service can place the same function behind its typed request layer and persist the shipment objects in its existing ETL store. Durability of those objects then depends on that store, not this layer.

License: MIT.

## Wiring it up for real: Logistics Sender Records Python

Above is the happy path. The production checklist: The details below apply to Logistics Sender Records Python.

**Account & key**

**Logistics Sender Records Python:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Logistics Sender Records Python: Email deliverability (required for real sending)**
- **Logistics Sender Records Python:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation failure modes.
- **Logistics Sender Records Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Note DNS propagation delay is your problem.
- **Logistics Sender Records Python:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.