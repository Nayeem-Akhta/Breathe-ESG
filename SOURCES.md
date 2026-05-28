# Sources

## Source 1 — SAP Fuel & Procurement

### Real-world format researched
SAP supports multiple export mechanisms. I researched:
- **IDoc (Intermediate Document):** XML-like EDI format used for
  system-to-system integration. Too complex for a file-based prototype.
- **OData services:** REST APIs exposed by SAP Gateway. Requires
  authenticated access to client's SAP system.
- **Flat file export via SE16/MB51:** Standard transaction-based
  CSV/text export available to any SAP user with reporting access.

**Chose:** Flat file CSV from MB51 (Material Document List transaction).
MB51 is the standard SAP report for material movements including
fuel consumption. It exports exactly the fields needed: plant,
material number, quantity, unit, and posting date.

### What I learned
- SAP column headers can appear in German in some regional
  configurations (WERKS, MENGE, MEINS, BUDAT are German abbreviations)
- Dates are in YYYYMMDD format, not ISO 8601
- Units use SAP internal codes (L, GAL, M3) not spelled-out words
- Plant codes are meaningless without a lookup table — "1000" is
  a common default plant code but means different things per client
- Material numbers (MATNR) are client-specific and require a
  material master lookup to get human-readable descriptions

### Sample data design
My sample data (`sap_fuel.csv`) includes:
- Diesel entries in litres (most common)
- A petrol entry to test material mapping
- A natural gas entry in M3 to test unit conversion
- A gallon entry (US plant) to test unit normalization
- An empty quantity row to test failure handling
- A bad date row to test date parsing failure
- An unknown plant code to test suspicious flagging
- A very high quantity to test value-based suspicious flagging

### What would break in real deployment
- Material numbers are client-specific — our MATERIAL_MAP would
  need to be populated from the client's SAP material master
- Some SAP configurations export additional columns we don't handle
- Files over ~50,000 rows need async processing
- Character encoding issues (SAP sometimes exports in Latin-1, not UTF-8)

---

## Source 2 — Utility Electricity

### Real-world format researched
I researched how Indian facilities teams typically access electricity
consumption data:
- **BESCOM (Bangalore):** Offers a consumer portal with monthly
  consumption history downloadable as PDF. No structured CSV export.
- **MSEDCL (Mumbai):** Similar portal, bill download as PDF.
- **Generic utility portals:** Most Indian utilities offer a
  "Download Bill" feature that produces PDFs, not CSVs.

For enterprise accounts (HT connections), utilities sometimes provide
consumption data to energy management platforms like Enertiv or
Schneider Electric's EcoStruxure, which can export CSV.

**Chose:** CSV export modeled on what an energy management platform
would produce, since enterprise clients with multiple sites typically
use such platforms to aggregate consumption across meters.

### What I learned
- Billing periods don't align with calendar months — bills run from
  meter reading date to meter reading date
- Large facilities have multiple meters (HT and LT connections)
- Units can be kWh, MWh, or even kVAh (kilovolt-ampere hours) —
  requiring normalization
- Indian grid emission factors vary significantly by region
  (IN_SOUTH: 0.708 vs IN_EAST: 0.916 kg CO2e/kWh per CEA 2023)
- Billing periods from different sites can overlap when data is
  aggregated — requires deduplication logic

### Sample data design
My sample data (`utility_electricity.csv`) includes:
- Multiple sites with different meter IDs
- A MWh entry to test unit conversion (×1000)
- Different grid zones to test regional emission factors
- An empty consumption row to test failure handling
- An overlapping billing period to test duplicate detection

### What would break in real deployment
- PDF bill parsing would be needed for clients without energy
  management platforms
- Some utilities provide kVAh not kWh — requires power factor
  correction to convert
- Multi-tenant buildings have shared meters requiring allocation logic
- Real-time API integration would require per-utility authentication

---

## Source 3 — Corporate Travel

### Real-world format researched
I researched Concur's Travel & Expense platform, which is the
dominant corporate travel platform in India and globally:
- **Concur Trip Report export:** Available as CSV from Concur's
  reporting module. Contains trip_id, traveler, dates, origin,
  destination, carrier, class, and cost.
- **Concur API (v4):** REST API with OAuth2 authentication.
  Requires per-company app registration and user consent flow.
- **Navan (formerly TripActions):** Similar structure to Concur,
  JSON API with similar fields.

**Chose:** CSV export modeled on Concur's Trip Report format, since
API integration requires OAuth setup impractical for a prototype.

### What I learned
- Flight distances are almost never included in travel platform exports
  — only origin and destination airport codes
- Hotel entries record nights and location but not distance
- Ground transport entries sometimes have distance, sometimes only
  cost
- Business class flights emit roughly 2.75× more CO2e than economy
  per the DEFRA multiplier (0.4286 vs 0.1553 kg CO2e/km)
- Layered itineraries (BLR→DXB→LHR) appear as two separate rows,
  not one
- Some platforms use city names instead of airport codes for hotels

### Sample data design
My sample data (`travel.csv`) includes:
- Flights with only airport codes (no distance) to test lookup logic
- A business class flight to test class-based emission factors
- Hotel entries (per night factor)
- Ground transport with explicit distance
- An invalid airport code pair to test suspicious flagging

### What would break in real deployment
- Airport code lookup table only covers ~20 common routes —
  production needs ICAO or OAG aviation distance API
- City-name hotels need geocoding to identify country for
  correct emission factor
- Multi-leg itineraries need deduplication logic
- Rental car emissions need vehicle type (petrol vs electric)