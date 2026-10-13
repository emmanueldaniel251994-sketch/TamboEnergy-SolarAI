# Manufacturer evidence in saved conversations

The saved AI Assistant now supports an optional registered equipment model and exact fault code. Select the exact physical equipment model in **Equipment details**, enter its code, and start or continue a saved case. The server looks up the current verified manufacturer records and shows matching descriptions with source-document links alongside general diagnostic guidance.

## Trust and safety behavior

- Model and code matching is exact. Codes are not padded, case-normalized, or guessed from general prose. Enter the exact code in the equipment field.
- Evidence requires the complete manufacturer → model → document → fault-code verification chain. Missing, pending, or revoked evidence yields an explicit no-verified-match result with no manufacturer descriptions or sources.
- Reported brand/model conflicts for recognized inverter, battery, or panel records withhold that model's evidence. Model aliases are not automatically inferred.
- Rejected diagnostic quality review, detected emergencies, and industrial-risk escalation prevent the manufacturer panel from supplying records. Previously withheld historical material is not upgraded while reopening a case.
- Registry corrective actions are not injected into the saved conversation. Description/action content matching the existing hazardous-action guard is withheld. This conservative keyword guard is not a guarantee that all document content is safe or technically correct.
- Descriptions are bounded excerpts (up to 1000 characters, at most five matches); open the cited source to review its full context. Evidence is advisory and never permission to work on energized equipment or bypass protections.

General guidance remains independent of the manufacturer evidence panel. Selecting a registry model is a user claim about physical equipment, not automatic identification of an installed device. Verified records do not establish that the user's physical system matches the selected model.

## Persistence and revocation

The model selection, code, and evidence snapshot are stored with each turn. Fresh turns use current registry verification status. Reopening a case rechecks stored evidence against current records and removes unavailable/revoked citations from the response without rewriting original conversation snapshots. Lookups are cached within that read for equivalent model/code/safety context, so repeated measurement updates do not require repeated evidence queries.

Revalidation occurs when a case is opened or a new turn is generated; an already displayed browser page is not live-updated when another administrator changes registry verification. Checked timestamps are displayed. Old messages without a manufacturer snapshot remain unchanged.

Choose **General guidance / no registered model** to explicitly clear the model selection on the next submitted turn. Other equipment fields retain their existing update behavior. If the registry list cannot load, general diagnostic conversations remain available.

## API and deployment

`EquipmentProfile` adds optional positive `equipment_model_id`; its existing `fault_code` field now accepts up to 100 characters. Conversation responses add `quality_review_passed` and nullable `manufacturer_evidence`. Existing clients can ignore those fields. Follow-up updates can explicitly set `equipment_model_id` to null.

No new database migration is needed for these JSON profile/metadata additions. Prior schema migrations, including PR #6's `a8d52f4c901e`, still need to be applied before serving the relevant API routes. Deploy the matching backend and frontend versions together. No production migration, deployment, or merge was performed during this work.

## Validation

Backend tests exercise exact matching, all unverified dependency levels, model conflicts, emergency/industrial/quality-review withholding, hazardous registry content, revocation on reopening, unchanged stored snapshots, follow-up persistence, clearing the selection, and per-read lookup caching. Frontend component tests verify selection payloads, source links, and clearing saved model IDs. Full build and lint retain existing warnings. Real-browser layout and deployed end-to-end integration remain unverified.
