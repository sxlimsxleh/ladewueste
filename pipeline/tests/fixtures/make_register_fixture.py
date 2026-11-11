"""Generate register_fixture.csv: a small, entirely invented register with every quirk of the real one.

The real Ladesäulenregister is never committed (rule 3), but CI must still run the full pipeline,
dbt tests included. This script writes ~60 made-up records in the real file's exact layout:
UTF-8 BOM, title/disclaimer lines padded with ';', a group-label row above the header, CRLF records
with line breaks inside quoted fields, German decimals, ';'-separated plug and kW lists, and one
example of each problem the cleaning rules handle. Operators, addresses and IDs are fictional.

Run: uv run python -m pipeline.tests.fixtures.make_register_fixture
"""

import csv
import io
from pathlib import Path

OUT = Path(__file__).resolve().parent / "register_fixture.csv"
N_GROUPS = 6
BASE = [
    "Ladeeinrichtungs-ID", "Betreiber", "Anzeigename (Karte)", "Status", "Art der Ladeeinrichtung",
    "Anzahl Ladepunkte", "Nennleistung Ladeeinrichtung [kW]", "Inbetriebnahmedatum", "Straße", "Hausnummer",
    "Adresszusatz", "Postleitzahl", "Ort", "Kreis/kreisfreie Stadt", "Bundesland", "Breitengrad", "Längengrad",
    "Standortbezeichnung", "Informationen zum Parkraum", "Bezahlsysteme", "Öffnungszeiten",
    "Öffnungszeiten: Wochentage", "Öffnungszeiten: Tageszeiten",
]
GROUP = ["Steckertypen{n}", "Nennleistung Stecker{n}", "EVSE-ID{n}", "Public Key{n}"]
HEADER = BASE + [c.format(n=n) for n in range(1, N_GROUPS + 1) for c in GROUP]

CCS = "DC Fahrzeugkupplung Typ Combo 2 (CCS)"
TYPE2 = "AC Typ 2 Steckdose"

# Town -> (lat, lon) inside Germany, all invented addresses.
TOWNS = {
    "Berlin": (52.520008, 13.404954), "Hamburg": (53.551086, 9.993682), "München": (48.137154, 11.576124),
    "Köln": (50.937531, 6.960279), "Frankfurt am Main": (50.110924, 8.682127), "Stuttgart": (48.775846, 9.182932),
    "Leipzig": (51.339695, 12.373075), "Hannover": (52.375892, 9.732010), "Nürnberg": (49.452030, 11.076750),
    "Dresden": (51.050407, 13.737262), "Kassel": (51.312711, 9.479746), "Erfurt": (50.984768, 11.029880),
}


def de(x: float, decimals: int = 6) -> str:
    """German decimal: 52.52 -> '52,52'."""
    return f"{x:.{decimals}f}".rstrip("0").rstrip(".").replace(".", ",")


def record(rid: int, operator: str, town: str, points: list[tuple[str, str, str]], *, station_kw: str | None = None,
           lat: str | None = None, lon: str | None = None, street: str = "Musterstraße", kind: str | None = None) -> list[str]:
    """points: (plug list, kW list, EVSE cell) per charging point, as raw cell text."""
    la, lo = TOWNS.get(town, (51.0, 10.0))
    kws = [float(k.replace(",", ".")) for _, kw, _ in points for k in kw.split(";")]
    row = {
        "Ladeeinrichtungs-ID": str(rid), "Betreiber": operator, "Anzeigename (Karte)": "", "Status": "In Betrieb",
        "Art der Ladeeinrichtung": kind or ("Schnellladeeinrichtung" if max(kws) > 22 else "Normalladeeinrichtung"),
        "Anzahl Ladepunkte": str(len(points)), "Nennleistung Ladeeinrichtung [kW]": station_kw or de(sum(kws), 1),
        "Inbetriebnahmedatum": f"{(rid % 28) + 1:02d}.0{(rid % 9) + 1}.2024", "Straße": street, "Hausnummer": str(rid % 50 + 1),
        "Adresszusatz": "", "Postleitzahl": "10115", "Ort": town, "Kreis/kreisfreie Stadt": town, "Bundesland": "Testland",
        "Breitengrad": lat if lat is not None else de(la), "Längengrad": lon if lon is not None else de(lo),
        "Standortbezeichnung": "", "Informationen zum Parkraum": "", "Bezahlsysteme": "RFID-Karte;Onlinezahlungsverfahren",
        "Öffnungszeiten": "247", "Öffnungszeiten: Wochentage": "", "Öffnungszeiten: Tageszeiten": "",
    }
    for n, (plugs, kw, evse) in enumerate(points, start=1):
        row[f"Steckertypen{n}"], row[f"Nennleistung Stecker{n}"], row[f"EVSE-ID{n}"] = plugs, kw, evse
    return [row.get(c, "") for c in HEADER]


def records() -> list[list[str]]:
    rows: list[list[str]] = []
    rid = 9_000_001

    def add(*args, **kwargs) -> None:
        nonlocal rid
        rows.append(record(rid, *args, **kwargs))
        rid += 1

    # Ordinary AC and DC stations across Germany (operator spellings vary: R06/R07/R08).
    for i, town in enumerate(TOWNS):
        operator = ["Stadtwerke Muster GmbH", "STADTWERKE MUSTER GMBH", "Testwerk Energie AG ", "Beispiel Mobil GmbH"][i % 4]
        add(operator, town, [(TYPE2, "22", f"DE*TST*E{i:04d}*1"), (TYPE2, "22", f"DE*TST*E{i:04d}*2")])
        add("Schnell Laden SE", town, [(CCS, "150", f"DE*SLS*E{i:04d}")])
    add("Stadtwerke Muster", "Erfurt", [(TYPE2, "11", "")])  # differs only by legal form: R08 suggestion

    # An HPC hub: one operator, 6 x 300 kW within a few metres in Kassel (site + hub).
    lat, lon = TOWNS["Kassel"]
    for k in range(6):
        add("Hub Betrieb GmbH", "Kassel", [(CCS, "300", f"DE*HUB*E{k:04d}")],
            lat=de(lat + k * 0.00003), lon=de(lon + k * 0.00003))

    # Multi-plug points, a plug/kW mismatch (R04), implausible power (R05).
    add("Stadtwerke Muster GmbH", "Berlin", [(f"{TYPE2}; AC Schuko", "22; 3,7", ""), ("DC CHAdeMO", "50", "")])
    add("Stadtwerke Muster GmbH", "Hamburg", [(f"{TYPE2}; AC Typ 2 Fahrzeugkupplung", "11", "")])
    add("Schnell Laden SE", "München", [(CCS, "300", "")], station_kw="1800")
    add("Schnell Laden SE", "Köln", [(CCS, "300", "")], station_kw="150")

    # Placeholder coordinate used in four towns (R10), far outside Germany.
    for town in ["Berlin", "Leipzig", "Dresden", "Nürnberg"]:
        add("Platzhalter GmbH", town, [(TYPE2, "22", "")], lat="54,32459", lon="7,36405")
    # A typo far outside (R09), a point near the border (accepted), whole degrees and low precision (R11).
    add("Stadtwerke Muster GmbH", "Hannover", [(TYPE2, "22", "")], lat="52,023038", lon="4")
    add("Grenzwerk GmbH", "Breisach", [(TYPE2, "22", "")], lat="48,029892", lon="7,579373")
    add("Stadtwerke Muster GmbH", "Stuttgart", [(TYPE2, "22", "")], lat="48", lon="9,182932")
    add("Stadtwerke Muster GmbH", "Frankfurt am Main", [(TYPE2, "22", "")], lat="50,11", lon="8,68")

    # EVSE cells: several IDs with line breaks, free text, a multi-line public key (R12)...
    add("Testwerk Energie AG ", "Leipzig", [(TYPE2, "22", "DE*TWE*E0001*1\nDE*TWE*E0001*2\n")])
    add("Testwerk Energie AG ", "Dresden", [(TYPE2, "22", "Ladezeiten 18:00-07:00")])
    # ...and the same valid EVSE-ID registered twice: a duplicate (R13).
    add("Doppel GmbH", "Erfurt", [(CCS, "150", "DE*DUP*E0001")])
    add("Doppel GmbH", "Erfurt", [(CCS, "150", "DE*DUP*E0001")])
    # A street with a non-breaking space (R06).
    add("Beispiel Mobil GmbH", "Nürnberg", [(TYPE2, "22", "")], street="Hauptstraße ")
    return rows


def main() -> None:
    pad = ";" * (len(HEADER) - 1)
    buffer = io.StringIO(newline="")
    buffer.write("﻿")
    for line in ["Ladesäulenregister Bundesnetzagentur (SYNTHETIC TEST FIXTURE - invented data)", "",
                 "Hinweis: ", "Diese Datei ist erfunden und dient nur den automatischen Tests.", "",
                 "Letzte Aktualisierung vom: 01.09.2026", ""]:
        buffer.write(line + pad[line.count(";"):] + "\r\n")
    groups = [""] * len(BASE) + [x for n in range(1, N_GROUPS + 1) for x in (f"{n}. Ladepunkt", "", "", "")]
    groups[0] = "Allgemeine Informationen"
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(groups)
    writer.writerow(HEADER)
    rows = records()
    rows[0][HEADER.index("Public Key1")] = "3059 3013 0607\n2a86 48ce 3d02"  # a key with a line break
    writer.writerows(rows)
    OUT.write_bytes(buffer.getvalue().encode("utf-8"))
    print(f"Wrote {OUT.name}: {len(rows)} records")


if __name__ == "__main__":
    main()
