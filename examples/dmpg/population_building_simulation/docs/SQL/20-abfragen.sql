-- =========================================
-- 1. Alle privaten Eigentümer (Personen)
-- =========================================
SELECT p.ssn,
       p.vorname,
       p.nachname,
       p.alter
FROM Person p
         JOIN Privateigentuemer pe ON p.ssn = pe.ssn;


-- =========================================
-- 2. Alle gewerblichen Eigentümer
-- =========================================
SELECT g.gewerbe_id,
       g.firmenname,
       g.ust_id
FROM Gewerbeeigentuemer g;


-- =========================================
-- 3. Barrierefreie Wohnungen
-- =========================================
SELECT wohnungsnummer,
       ausstattung,
       bewohner_anzahl
FROM Wohnung
WHERE barrierefrei = TRUE;


-- =========================================
-- 4. Eigentümer mit ihren Wohnungen
-- (über Mietverhältnis)
-- =========================================
SELECT p.vorname,
       p.nachname,
       w.wohnungsnummer,
       w.ausstattung
FROM Mietverhaeltnis m
         JOIN Wohnung w ON m.wohnungsnummer = w.wohnungsnummer
         JOIN Eigentuemer e ON m.eigentuemer_id = e.eigentuemer_id
         JOIN Privateigentuemer pe ON e.eigentuemer_id = pe.eigentuemer_id
         JOIN Person p ON pe.ssn = p.ssn;


-- =========================================
-- 5. Alle Personen mit ihren Zeitplänen
-- =========================================
SELECT p.vorname,
       p.nachname,
       z.startzeit,
       z.endzeit,
       z.wochentag
FROM Person p
         LEFT JOIN Personenzeitplan pz ON p.ssn = pz.ssn
         LEFT JOIN Zeitplan z ON pz.zeitplan_id = z.zeitplan_id;


-- =========================================
-- 6. Alle Wohnungen mit Adresse
-- =========================================
SELECT w.wohnungsnummer,
       w.ausstattung,
       a.strasse,
       a.hausnummer,
       a.plz,
       a.stadt
FROM Wohnung w
         JOIN Gebaeude g ON w.gebaeude_id = g.gebaeude_id
         JOIN Adresse a ON g.gebaeude_id = a.gebaeude_id;


-- =========================================
-- 7. Personen und ihre Bedürfnisse
-- =========================================
SELECT p.vorname,
       p.nachname,
       b.name AS beduerfnis,
       b.prioritaet
FROM Person p
         JOIN Personenbeduerfnisse pb ON p.ssn = pb.ssn
         JOIN Beduerfnis b ON pb.beduerfnis_id = b.beduerfnis_id;


-- =========================================
-- 8. Personen mit hoch priorisierten Bedürfnissen
-- =========================================
SELECT p.vorname,
       p.nachname,
       b.name,
       b.prioritaet
FROM Person p
         JOIN Personenbeduerfnisse pb ON p.ssn = pb.ssn
         JOIN Beduerfnis b ON pb.beduerfnis_id = b.beduerfnis_id
WHERE b.prioritaet >= 80;


-- =========================================
-- 9. Durchschnittliche Bewohnerzahl pro Stadt
-- =========================================
SELECT a.stadt,
       AVG(w.bewohner_anzahl) AS durchschnitt_bewohner
FROM Wohnung w
         JOIN Gebaeude g ON w.gebaeude_id = g.gebaeude_id
         JOIN Adresse a ON g.gebaeude_id = a.gebaeude_id
GROUP BY a.stadt;


-- =========================================
-- 10. Ziele mit Koordinaten
-- =========================================
SELECT z.name AS ziel,
       k.breitengrad,
       k.laengengrad
FROM Ziel z
         JOIN Koordinaten k ON z.koordinaten_id = k.koordinaten_id;


-- =========================================
-- 11. Aktivitäten mit Dauer
-- =========================================
SELECT z.name AS ziel,
       a.startzeit,
       a.endzeit,
       TIMEDIFF(a.endzeit, a.startzeit) AS dauer
FROM Aktivitaet a
         JOIN Ziel z ON a.ziel_id = z.ziel_id;


-- =========================================
-- 12. Kurze und lange Aktivitäten (UNION)
-- =========================================
-- Kurze Aktivitäten (< 1 Stunde)
SELECT z.name AS ziel,
       TIMEDIFF(a.endzeit, a.startzeit) AS dauer,
       'Kurz' AS typ
FROM Aktivitaet a
         JOIN Ziel z ON a.ziel_id = z.ziel_id
WHERE TIMEDIFF(a.endzeit, a.startzeit) < '01:00:00'

UNION

-- Lange Aktivitäten (> 2 Stunden)
SELECT z.name AS ziel,
       TIMEDIFF(a.endzeit, a.startzeit) AS dauer,
       'Lang' AS typ
FROM Aktivitaet a
         JOIN Ziel z ON a.ziel_id = z.ziel_id
WHERE TIMEDIFF(a.endzeit, a.startzeit) > '02:00:00';


-- =========================================
-- 13. Anzahl Wohnungen pro Eigentümer
-- =========================================
SELECT e.eigentuemer_id,
       COUNT(m.wohnungsnummer) AS anzahl_wohnungen
FROM Eigentuemer e
         LEFT JOIN Mietverhaeltnis m ON e.eigentuemer_id = m.eigentuemer_id
GROUP BY e.eigentuemer_id;


-- =========================================
-- 14. Bewohner mit Haustieren
-- =========================================
SELECT p.vorname,
       p.nachname
FROM Bewohner b
         JOIN Person p ON b.ssn = p.ssn
WHERE b.haustier = TRUE;
