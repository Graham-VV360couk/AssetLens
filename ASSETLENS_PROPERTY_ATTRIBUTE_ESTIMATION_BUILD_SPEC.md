# AssetLens — Property Attribute Estimation Build Spec

## Purpose

Build a new **Property Attribute Estimation** layer inside **AssetLens** (`assetlens.geekybee.net`) that can estimate, infer, and display likely residential property characteristics when exact data is not available.

The system must **not pretend certainty where certainty does not exist**.

This feature should help users quickly assess a property by combining:
- directly known facts
- inferred attributes
- estimated attributes
- confidence scores
- source traceability

The output should support property investors, developers, HMO researchers, and due diligence workflows.

---

## Core Product Goal

Given a property record, AssetLens should attempt to determine or estimate:

1. **Property type**
   - Detached
   - Semi-detached
   - Terraced
   - End terrace
   - Mid terrace
   - Flat / apartment
   - Maisonette
   - Bungalow
   - Chalet bungalow
   - Other / unknown

2. **Bedrooms**
   - exact if known
   - estimated if inferred

3. **Bathrooms**
   - exact if known
   - estimated or range if inferred

4. **Social / reception spaces**
   - reception rooms
   - lounge(s)
   - dining room / kitchen diner / open plan social space
   - study / family room where relevant
   - this may need to be represented as an approximate count or structured summary

5. **Internal floor area**
   - sq ft and sqm
   - direct if known
   - estimated if derived

6. **Land / plot size**
   - sqm / sq ft / acres if possible
   - exact if known
   - approximate if inferred from parcel / geometry / external data

7. **Supporting characteristics where possible**
   - likely building form
   - likely extension status
   - likely loft conversion presence
   - outbuilding / garage indicators
   - garden size band
   - HMO suitability hints later

---

## Important Product Rule

Every returned attribute must be labelled as one of:

- **Known**
- **Inferred**
- **Estimated**
- **Unknown**

And every non-unknown field should carry:

- confidence score
- source type
- explanation / reasoning note
- last updated date if applicable

This must be a core architectural principle.

Do not build a system that outputs naked values with no traceability.

---

## Output Behaviour Example

Example property card output:

- Property Type: Semi-detached  
  Status: Known  
  Confidence: 0.98  
  Source: Land Registry

- Bedrooms: 3  
  Status: Estimated  
  Confidence: 0.81  
  Source: Floor area + local comparable model

- Bathrooms: 1–2  
  Status: Estimated  
  Confidence: 0.52  
  Source: Statistical inference

- Reception / Social Areas: 2  
  Status: Inferred  
  Confidence: 0.61  
  Source: Listing text / floor area pattern

- Internal Area: 1,040 sq ft  
  Status: Known  
  Confidence: 0.96  
  Source: EPC

- Plot Size: 0.08 acres  
  Status: Estimated  
  Confidence: 0.74  
  Source: footprint + parcel geometry

---

## Build Objectives

### Objective 1 — Create a Property Attribute Estimation Engine

Create a modular backend engine that:
- accepts a property record
- pulls together available facts
- calculates likely attributes
- returns structured outputs
- includes confidence and provenance metadata

This should be implemented as a reusable service, not hardcoded into a controller.

Suggested service name:

`PropertyAttributeEstimator`

Possible structure:

- `PropertyAttributeEstimator`
- `PropertyFactCollector`
- `PropertyInferenceEngine`
- `PropertyConfidenceScorer`
- `PropertyExplanationBuilder`

---

## Objective 2 — Define the Attribute Data Model

Create a clean internal schema for estimated property attributes.

Suggested structure:

```json
{
  "property_type": {
    "value": "semi_detached",
    "label": "Semi-detached",
    "status": "known",
    "confidence": 0.98,
    "source": "land_registry",
    "explanation": "Matched to transaction property type",
    "last_updated": "2026-03-10"
  },
  "bedrooms": {
    "value": 3,
    "status": "estimated",
    "confidence": 0.81,
    "source": "inference_model",
    "explanation": "Estimated from floor area, comparable local properties, and dwelling type"
  },
  "bathrooms": {
    "value": {
      "min": 1,
      "max": 2
    },
    "status": "estimated",
    "confidence": 0.52,
    "source": "inference_model",
    "explanation": "Low-confidence range estimate"
  },
  "reception_rooms": {
    "value": 2,
    "status": "inferred",
    "confidence": 0.61,
    "source": "listing_text_parser",
    "explanation": "Detected wording indicating two living/social spaces"
  },
  "floor_area": {
    "value_sqft": 1040,
    "value_sqm": 96.6,
    "status": "known",
    "confidence": 0.96,
    "source": "epc"
  },
  "plot_size": {
    "value_acres": 0.08,
    "status": "estimated",
    "confidence": 0.74,
    "source": "geospatial_estimation"
  }
}
Objective 3 — Establish Source Priority Rules

The system must use a priority-based merge model for facts.

Example source priority
Property type

explicit registry / authoritative transaction data

EPC / authoritative housing data

listing extraction

footprint / geometry model

statistical model

Bedrooms

explicit listing or user-confirmed value

structured housing data if available

EPC / floor area plus pattern rules

local comparable inference model

Bathrooms

listing extraction

user-confirmed value

comparable inference

floor area pattern model

Floor area

EPC or authoritative structured housing source

listing extraction

footprint x floors heuristic

local comparable inference

Plot size

parcel/title/geometry data

listing extraction

boundary approximation

geospatial estimate

Implement configurable source priority rules so this can evolve.

Objective 4 — Build Confidence Scoring

Every estimated/inferred field must get a confidence score between 0.00 and 1.00.

Confidence should consider:

number of agreeing sources

quality / authority of source

recency of source

closeness of model fit

ambiguity in property type

completeness of underlying input data

contradiction between sources

Suggested confidence bands

0.90–1.00 = Very High

0.75–0.89 = High

0.55–0.74 = Moderate

0.35–0.54 = Low

<0.35 = Very Low

Add a display-friendly label as well as raw score.

Objective 5 — Build Rule-Based Inference First

For MVP, prioritise rule-based estimation before machine learning.

Use rule-based logic for:

bungalow likelihood from property type wording / building geometry

bedroom estimates from floor area bands + dwelling type

bathroom estimates from bedroom count + floor area

reception estimates from property size bands

plot size estimates from footprint / parcel ratios

garden size band from plot minus footprint

Example heuristic logic

These are examples only and should be configurable:

Terraced house 70–95 sqm → likely 2–3 bedrooms

Semi-detached 85–120 sqm → likely 3 bedrooms

Detached 140–220 sqm → likely 4–5 bedrooms

Bungalow 55–90 sqm → likely 2 bedrooms

4 bedrooms often correlates with 2+ bathrooms, but confidence may still be moderate only

All rules should be stored in a configurable format where possible.

Objective 6 — Create an Explanation Layer

For every inferred or estimated value, return a short explanation string.

Examples:

"Estimated from EPC floor area and local dwelling pattern"

"Classified as bungalow based on listing text and single-storey footprint shape"

"Plot size estimated from parcel geometry minus built footprint"

"Bathroom range inferred due to missing direct source data"

This explanation must be user-facing and admin-debug friendly.

Objective 7 — Design UI Presentation

Add a new AssetLens section:

Property Profile

Suggested grouped layout:

Verified Facts

Fields with high-authority direct evidence

Strong Inferences

Fields with strong but indirect evidence

Estimated Attributes

Useful estimates with confidence shown

Missing / Unknown

Fields that cannot currently be supported

UI rules

show confidence badge

show status badge (Known / Inferred / Estimated / Unknown)

show source badge

allow hover or click for explanation

allow admin / advanced users to inspect raw evidence later

Objective 8 — Add User Override Capability

Users should be able to manually correct or override key fields:

property type

bedrooms

bathrooms

reception/social rooms

floor area

plot size

bungalow flag

extension flag

Requirements

store original estimated value

store user override value

store override source as user_override

preserve audit trail

do not overwrite raw computed results

computed and overridden values should coexist

Suggested structure:

computed_value

display_value

override_value

override_note

override_user_id

override_timestamp

Objective 9 — Make This Extensible for Future HMO and Investment Scoring

Design this feature so it later supports:

HMO suitability scoring

development potential

extension potential

loft conversion opportunities

rental yield modelling

valuation assistance

deal comparison scoring

The current architecture should therefore avoid being too narrow.

Technical Build Requirements
Backend

Please implement:

service class for attribute estimation

source merge logic

confidence scoring logic

explanation builder

optional per-field estimator classes if cleaner

structured output transformer for frontend/API

Suggested pattern:

app/Services/PropertyAttributeEstimator.php

app/Services/PropertyFacts/FactCollector.php

app/Services/PropertyFacts/SourceResolver.php

app/Services/PropertyInference/BedroomEstimator.php

app/Services/PropertyInference/BathroomEstimator.php

app/Services/PropertyInference/ReceptionEstimator.php

app/Services/PropertyInference/PlotEstimator.php

app/Services/PropertyInference/PropertyTypeEstimator.php

app/Services/PropertyInference/ConfidenceScorer.php

app/Services/PropertyInference/ExplanationBuilder.php

Use the actual stack and naming conventions already present in the app if different.

Database / Persistence

If persistence is needed, create a table or JSON field structure to store computed outputs.

Possible options:

Option A — JSON column on properties table

Store latest computed profile in JSON.

Option B — Separate table

property_attribute_profiles

Suggested fields:

id

property_id

computed_payload_json

version

generated_at

generated_by

source_summary_json

override_payload_json

display_payload_json

Add versioning if practical so recalculation changes can be tracked.

API Requirements

Expose an endpoint or extend existing property detail response to return:

estimated attributes

status

confidence

source

explanation

override state

timestamps

Suggested response node:

{
  "property_profile": {
    ...
  }
}
Frontend Requirements

Frontend must:

display structured attribute cards cleanly

distinguish known vs estimated

avoid misleading presentation

show ranges where precision is weak

show "unknown" gracefully

support future admin evidence drilldown

Suggested UI components:

PropertyProfileCard

AttributeConfidenceBadge

AttributeSourceBadge

AttributeExplanationPopover

PropertyProfileOverridePanel

MVP Scope

For first release, prioritise:

property type

floor area

bedrooms

bathrooms

reception/social areas

plot size

MVP rules

do not block on machine learning

do not wait for perfect external data integrations

build with mockable source adapters

use available property data first

where data is missing, use configurable heuristics

Non-Goals for MVP

Do not attempt all of this in first release:

full machine learning pipeline

satellite image classification model

automated title plan OCR

highly granular room-by-room layouts

guaranteed planning or HMO compliance scoring

exact valuations from this module alone

Those can come later.

Important UX Principle

This feature should make AssetLens feel:

intelligent

honest

useful

investor-friendly

It must not feel:

vague

overconfident

misleading

"AI guessed this, trust us bro"

In other words: no techno-wizard nonsense.

Suggested Heuristic Examples

Please implement a configurable ruleset for first-pass estimation.

Bedrooms

Use combinations of:

floor area band

property type

local comparables if available

listing text extraction if available

Bathrooms

Use combinations of:

bedroom estimate

floor area

detached/semi/terrace/flat type

price band if useful

listing extraction if available

Reception / social areas

Use:

property type

floor area

listing language

typical UK housing layout assumptions

Bungalow

Consider:

explicit wording

low height / single-storey hints if data exists

footprint proportions

comparable dwelling records nearby

Plot size

Consider:

parcel geometry

footprint area

local density pattern

set-back and garden depth patterns if data exists

Make these heuristics easy to tune later.

Admin / Developer Debug View

Please include a developer/admin-friendly debug output showing:

input facts used

discarded facts

chosen sources

confidence calculations

reasoning strings

contradictions found

This can be behind an admin flag or debug mode only.

This will be essential for refinement.

Test Coverage Required

Please add tests for:

Unit tests

bedroom estimation rules

bathroom estimation rules

property type resolution

confidence scoring

source priority selection

override handling

explanation text generation

Feature / integration tests

property with authoritative data only

property with partial data

property with conflicting data

property with almost no data

property with user override

property with range-based estimate

frontend/API output structure

Edge cases

flat vs maisonette ambiguity

end terrace vs mid terrace ambiguity

bungalow false positives

unusually large terraced property

converted property with inconsistent signals

no EPC and no listing

malformed or incomplete source data

Deliverables

Please produce:

backend estimation engine

structured schema for property profile output

API exposure

frontend Property Profile section

override support

confidence and explanation layer

tests

developer notes explaining:

assumptions made

rule logic

future extension points

Build Order

Recommended implementation order:

define output schema

build source resolver

implement property type estimator

implement floor area resolver

implement bedroom estimator

implement bathroom estimator

implement reception/social estimator

implement plot size estimator

add confidence scoring

add explanation builder

expose via API

render in UI

add user override layer

add tests

add debug/admin evidence view

Final Instruction

Please build this as a trustworthy estimation layer, not just a guessed summary blob.

AssetLens should become stronger by showing:

what it knows

what it thinks

how sure it is

why it thinks that

That distinction is the entire value.

Where implementation choices are unclear, prefer:

modularity

transparency

auditability

future expandability

low risk of misleading users


If you want, I can also turn this into a **downloadable `.md` file** named something like:

## Objective 10 — Immediate Re-evaluation on Manual Edits

When a user manually edits or overrides any property attribute, the system must immediately trigger a **re-evaluation of the Property Attribute Estimation Engine** using the modified data as an input fact.

### Behaviour Requirements

User overrides should not simply replace the displayed value.

Instead they must:

1. Be stored as a **trusted input fact**
2. Trigger a **full recalculation of dependent attributes**
3. Update confidence scoring and explanations
4. Refresh the Property Profile output immediately

This ensures the system remains internally consistent.

### Example

Initial system estimate:

Bedrooms: 3  
Bathrooms: 1–2  
Reception rooms: 2  

User correction:

Bedrooms → 4

System response:

The estimation engine should immediately re-run using the new input.

Possible recalculated result:

Bedrooms: 4 (User Override)  
Bathrooms: 2 (Re-estimated based on updated bedroom count)  
Reception rooms: 2–3 (Adjusted estimate)  

### Override Data Model

Each override must store:

- field name
- override value
- override user
- override timestamp
- optional override note
- override source (`user_override`)

Example:

```json
{
  "bedrooms": {
    "computed_value": 3,
    "override_value": 4,
    "display_value": 4,
    "status": "user_override",
    "confidence": 1.0,
    "source": "user_override",
    "override_user_id": 102,
    "override_timestamp": "2026-03-10T14:10:00Z"
  }
}
Rescan Trigger

When an override occurs, the system must trigger:

PropertyAttributeEstimator.recalculate(property_id)

This recalculation must:

include override values as high-priority inputs

preserve original computed values for audit/debug

update dependent attribute estimates

regenerate confidence scores

regenerate explanation text

Dependency Behaviour

Overrides should affect any attributes that depend on them.

Example dependency chain:

Bedrooms
→ Bathroom estimate
→ Reception room estimate
→ HMO suitability scoring (future module)

Performance Considerations

To avoid unnecessary load:

Re-evaluation should be property scoped

Use cached source facts where possible

Only recompute dependent estimators when necessary

UX Requirement

After an override is saved:

the property profile should refresh automatically

recalculated fields should update immediately

recalculated explanations should reference the override where relevant

Example explanation:

"Bathroom estimate updated following user-confirmed bedroom count."


---

One small product insight here that will help AssetLens feel *very intelligent*:

You can show a subtle UI indicator like:

**“Recalculated using your update”**

That tells the user the system actually **reasoned with their correction**, rather than just accepting it.

If you'd like, I can also add one more powerful feature to the spec:  
**“Data contradiction detection”** — where the system flags things like:

> *User entered 5 bedrooms but floor area is only 65 sqm.*

That kind of feedback loop would make AssetLens feel extremely sharp.